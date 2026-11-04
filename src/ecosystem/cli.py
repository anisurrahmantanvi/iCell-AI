"""Command line interface (the human's control panel)."""
import sys


from .agents.base import Context
from .agents.orchestrator import run_task
from .core import audit, killswitch, proposals
from .core.killswitch import Stopped
from .evals.runner import load_last, run_eval, save_last
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


def cmd_eval(_):
    provider = get_provider()
    print(f"provider={provider.name}")
    avg, results = run_eval(provider, on_result=_show)
    save_last(results)
    print(f"গড় স্কোর: {avg:.3f}")


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
    print("বর্তমান প্রম্পট দিয়ে:")
    base, _r = run_eval(provider, on_result=_show)
    print("প্রস্তাবিত প্রম্পট দিয়ে:")
    new, _r = run_eval(provider, overrides={p["target"]: p["new_prompt"]}, on_result=_show)
    print(f"\nআগে: {base:.3f}  পরে: {new:.3f}")
    print("সতর্কতা: LLM রিভিউয়ার গোলমেলে, ছোট পার্থক্য প্রমাণ নয়। কয়েকবার চালান।")


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
    except (KeyError, ValueError) as e:
        sys.exit(f"ত্রুটি: {e}")
