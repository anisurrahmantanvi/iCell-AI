"""Command line interface (the human's control panel)."""
import sys

from .agents.base import Context
from .agents.orchestrator import run_task
from .core import audit, killswitch, proposals
from .core.killswitch import Stopped
from .evals.runner import load_last, run_eval_many, save_last, summarize
from .evolution.improver import propose
from .llm import get_provider


def cmd_run(args):
    if not args:
        sys.exit('ব্যবহার: ecosystem run "আপনার কাজ"')
    res = run_task(" ".join(args), Context(provider=get_provider()))
    print("প্ল্যান:", res["plan"])
    print("\nউত্তর:\n" + res["answer"])
    print(f"\nরিভিউয়ার স্কোর: {res['score']}/10 — {res['feedback']}")


def _show(res):
    print(f"  - {res['task'][:55]}... reviewer={res['score']:.1f}/10 checks={res['check']:.0%}")


def _parse_runs(args):
    """--runs N (1-5, default 1)."""
    if "--runs" not in args:
        return 1
    try:
        n = int(args[args.index("--runs") + 1])
    except (IndexError, ValueError):
        sys.exit("ব্যবহার: --runs সংখ্যা  (যেমন --runs 3)")
    return max(1, min(n, 5))


def _fmt(avgs):
    mean, lo, hi = summarize(avgs)
    if len(avgs) == 1:
        return f"{mean:.3f}"
    return f"{mean:.3f} (সর্বনিম্ন {lo:.3f}, সর্বোচ্চ {hi:.3f}, {len(avgs)} রান)"


def cmd_eval(args):
    args = args or []
    provider = get_provider()
    runs = _parse_runs(args)
    print(f"provider={provider.name} runs={runs}")
    on_run = (lambda i, avg: print(f"  -> রান {i}: {avg:.3f}")) if runs > 1 else None
    avgs, results = run_eval_many(provider, runs, on_result=_show, on_run=on_run)
    save_last(results)
    print(f"গড় স্কোর: {_fmt(avgs)}")


def cmd_improve(_):
    if load_last() is None:
        print("আগে `eval` চালানো হচ্ছে...")
        cmd_eval(None)
    results = load_last()
    pid = propose(results, Context(provider=get_provider()))
    if pid is None:
        print("প্রস্তাব বাতিল (ভুল target বা অস্বাভাবিক দৈর্ঘ্য)। বিস্তারিত audit log-এ।")
        return
    p = proposals.get(pid)
    print(f"নতুন প্রস্তাব #{pid} ({p['target']}): {p['reason']}")
    print(f"এখনো কিছু বদলায়নি। যাচাই: `test {pid}`, গ্রহণ: `approve {pid}`")


def cmd_proposals(_):
    for p in proposals.all_proposals():
        print(f"#{p['id']} [{p['status']}] {p['target']}: {p['reason']}")
        print(f"    নতুন প্রম্পট: {p['new_prompt'][:150]}")


def cmd_test(args):
    if not args:
        sys.exit("প্রস্তাবের নম্বর দিন")
    p = proposals.get(args[0])
    provider = get_provider()
    runs = _parse_runs(args)
    print("বর্তমান প্রম্পট দিয়ে:")
    base, _r = run_eval_many(provider, runs, on_result=_show)
    print("প্রস্তাবিত প্রম্পট দিয়ে:")
    new, _r = run_eval_many(provider, runs, overrides={p["target"]: p["new_prompt"]}, on_result=_show)
    b_mean, b_lo, b_hi = summarize(base)
    n_mean, n_lo, n_hi = summarize(new)
    print(f"\nআগে: {_fmt(base)}\nপরে: {_fmt(new)}")
    if runs == 1:
        print("সতর্কতা: ১টা রান, স্কোর নিজে নিজে কতটা ওঠানামা করে তা জানা নেই। --runs 3 দিয়ে চালান।")
    elif abs(n_mean - b_mean) <= max(b_hi - b_lo, n_hi - n_lo):
        print("ফল: পার্থক্য স্কোরের স্বাভাবিক ওঠানামার মধ্যে, উন্নতি প্রমাণিত নয়।")
    else:
        print("ফল: পার্থক্য ওঠানামার চেয়ে বড়। তবু কাজের সংখ্যা কম হলে নিশ্চিত নয়, আরও রান করে দেখুন।")


def _ask_human(p):
    print(f"{p['target']} প্রম্পট বদলাবে:\n--- নতুন ---\n{p['new_prompt']}\n")
    return input("অনুমোদন দিচ্ছেন? (y/N) ").strip().lower() == "y"


def cmd_approve(args):
    if not args:
        sys.exit("প্রস্তাবের নম্বর দিন")
    if proposals.approve(args[0], _ask_human):
        print("প্রয়োগ হয়েছে। পুরনো সংস্করণ state/history/-তে আছে।")
    else:
        print("বাতিল।")


def cmd_kill(_):
    killswitch.engage()
    audit.log("kill")
    print("STOP চালু। সব কাজ পরের মডেল কলের আগে থেমে যাবে।")


def cmd_resume(_):
    killswitch.release()
    audit.log("resume")
    print("STOP সরানো হয়েছে।")


def cmd_serve(args):
    from .api.server import serve
    host, port = "127.0.0.1", 8080
    if "--host" in args:
        host = args[args.index("--host") + 1]
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
    serve(host, port)


COMMANDS = {"serve": cmd_serve, "run": cmd_run, "eval": cmd_eval, "improve": cmd_improve, "proposals": cmd_proposals,
            "test": cmd_test, "approve": cmd_approve, "kill": cmd_kill, "resume": cmd_resume}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print("কমান্ড:", ", ".join(COMMANDS))
        return
    try:
        COMMANDS[argv[0]](argv[1:])
    except Stopped as e:
        audit.log("stopped", reason=str(e))
        print("\n⛔", e)
    except KeyboardInterrupt:
        audit.log("stopped", reason="Ctrl+C")
        print("\n⛔ Ctrl+C: বন্ধ করা হলো।")
    except RuntimeError as e:  # model/network failure (e.g. HTTP 429 rate limit, bad model name)
        audit.log("model_error", error=str(e)[:300])
        sys.exit(f"\nমডেল/নেটওয়ার্ক ত্রুটি: {e}")
    except (KeyError, ValueError) as e:
        sys.exit(f"ত্রুটি: {e}")
