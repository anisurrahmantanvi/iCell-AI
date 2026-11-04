# স্থাপত্য (Architecture)

লক্ষ্য: একাধিক AI এজেন্ট একসাথে কাজ করবে ও নিজেদের প্রম্পট উন্নত করার *প্রস্তাব* দেবে, কিন্তু মালিক (আপনি) সব সময় নিয়ন্ত্রণে থাকবেন।

## স্তর (layers)

```
            ┌─────────────────────────────┐
  আপনি ───▶ │ cli.py   (পরে: api/ HTTP)    │  মানুষের কন্ট্রোল প্যানেল
            └──────────────┬──────────────┘
                           │
     ┌─────────────────────┼──────────────────────┐
     ▼                     ▼                      ▼
 agents/               evolution/              evals/
 planner→worker        improver: শুধু          নির্দিষ্ট টেস্ট কাজ,
 →reviewer             প্রস্তাব লেখে           ৫০% রিভিউয়ার + ৫০% কিওয়ার্ড চেক
 (orchestrator)              │
     │                       ▼
     │               core/proposals.py ◀── মানুষের approve ছাড়া প্রয়োগ হয় না
     ▼
 agents/base.ask()  ◀── মডেল কলের একমাত্র দরজা
     │   ├─ core/killswitch  (STOP ফাইল)
     │   ├─ core/budget      (কল ও সময়ের সীমা)
     │   └─ core/audit       (সব লগ)
     ▼
 llm/  provider: mock | ollama | gemini | groq | (পরে আপনার API)
```

## ফোল্ডার

| পথ | কাজ | এজেন্ট বদলাতে পারে? |
|---|---|---|
| `src/ecosystem/core/` | kill switch, budget, audit, proposals/approval | না |
| `locked/` | নিয়ম (`rules`), `reviewer`, `improver` প্রম্পট | না |
| `prompts/` | `planner`, `worker` প্রম্পট | শুধু প্রস্তাব, মানুষের অনুমোদনে |
| `src/ecosystem/agents/` | এজেন্টের ভূমিকা | না (কোড) |
| `src/ecosystem/llm/` | মডেল প্রোভাইডার | না |
| `src/ecosystem/evals/`, `evals/tasks.json` | মাপার পদ্ধতি ও টেস্ট কাজ | না |
| `src/ecosystem/api/` | HTTP API (দুই-টোকেন: user / owner) | না |
| `state/` | STOP, audit.jsonl, proposals, history (git-ignored) | লগ ছাড়া না |

## অপরিবর্তনীয় নিয়ম (invariants)

1. সব মডেল কল `agents/base.ask()` দিয়ে যায়, সেখানে kill switch ও budget প্রতিবার চেক হয়।
2. প্রস্তাবের target শুধু `config.EVOLVABLE` (planner, worker) হতে পারে। বিচারক (reviewer), improver ও নিয়ম কখনো প্রস্তাবের আওতায় নেই।
3. `proposals.approve()` একটা `confirm` কলব্যাক চায়। CLI-তে সেটা টার্মিনালে আপনার `y`। কোনো এজেন্ট কোড এটা নিজে ডাকে না।
4. প্রতিটি প্রয়োগের আগে পুরনো প্রম্পট `state/history/`-তে সেভ হয়।
5. উন্নতি মাপা হয় আগে থেকে ঠিক করা টেস্টে, শুধু এজেন্টের নিজের মূল্যায়নে নয়।

## API কোথায় বসবে

- **মডেল API** (Gemini, OpenAI, Anthropic ইত্যাদি): `src/ecosystem/llm/` এ একটা নতুন ফাইল, `chat(system, user, role)` মেথডসহ একটা ক্লাস, আর `llm/__init__.py`-তে এক লাইন। বাকি কিছু বদলাতে হবে না।
- **HTTP API** (বাইরে থেকে চালানোর জন্য): `src/ecosystem/api/server.py`, তৈরি আছে। CLI-র মতোই একই ফাংশন ডাকে। `approve` ও `resume` শুধু owner টোকেনে হয়, `kill` যেকোনো বৈধ টোকেনে। অনুরোধ ও ভুল audit log-এ যায়।

## পরের ধাপ (প্রস্তাব)

1. আসল মডেল (Ollama বা ফ্রি API) দিয়ে `eval` চালিয়ে বেসলাইন নেওয়া।
2. `tasks.json` বাড়ানো, যাতে স্কোর আরও নির্ভরযোগ্য হয়।
3. এজেন্টদের টুল (ফাইল, সার্চ, কোড চালানো) যোগ করা, sandbox-এ, প্রতিটি টুলের জন্য আলাদা অনুমতি সহ।
