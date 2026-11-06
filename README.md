# iCell-AI

Multi-Agent AI Ecosystem।

মানুষের নিয়ন্ত্রণে চলা ছোট multi-agent সিস্টেম। এজেন্টরা কাজ ভাগ করে করে, নিজেদের প্রম্পট উন্নত করার *প্রস্তাব* দেয়, আপনি অনুমোদন দিলে তবেই প্রয়োগ হয়। বিস্তারিত: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)।

## চালানো (Python 3.9+, কিছু install লাগে না)

```
export PYTHONPATH=src
python -m ecosystem eval                 # mock মডেল দিয়ে (ডিফল্ট)
python -m ecosystem eval --runs 3        # ৩বার চালিয়ে গড় ও ওঠানামা (সর্বোচ্চ ৫)
python -m ecosystem run "আপনার কাজ"
python -m ecosystem report               # শেষ eval-এ কোথায় নম্বর কাটা গেল (অফলাইন, কোনো API কল নেই)
python -m ecosystem improve              # প্রস্তাব তৈরি (Improver ব্যর্থ চেকগুলো দেখে)
python -m ecosystem proposals
python -m ecosystem test 1 --runs 3      # আগে/পরে তুলনা, ওঠানামার সাথে মিলিয়ে
python -m ecosystem approve 1            # y দিলে প্রয়োগ
python -m ecosystem kill                 # Kill switch
python -m ecosystem resume
```

(`pip install -e .` করলে `ecosystem eval` সরাসরিও চলবে।)

## মডেল বেছে নেওয়া

| মডেল | সেটআপ |
|---|---|
| mock (শুধু পরীক্ষা, নকল উত্তর) | ডিফল্ট |
| Ollama (লোকাল, ফ্রি) | `export PROVIDER=ollama` |
| Gemini ফ্রি টিয়ার | `export PROVIDER=gemini GEMINI_API_KEY=...` |
| Groq ফ্রি টিয়ার | `export PROVIDER=groq GROQ_API_KEY=...` |

`MODEL=` দিয়ে মডেলের নাম বদলানো যায় (Groq-এর ডিফল্ট `openai/gpt-oss-20b`)। বাজেট: `MAX_CALLS` (৬০), `MAX_SECONDS` (৯০০)। `eval`-এর বাজেট নিজে কাজের সংখ্যা অনুযায়ী বাড়ে, তবে আপনি `MAX_CALLS`/`MAX_SECONDS` সেট করলে সেটাই মানা হয়।

**ভূমিকা অনুযায়ী আলাদা মডেল:** `PROVIDER_<ROLE>` ও `MODEL_<ROLE>` (ROLE = `PLANNER`, `WORKER`, `REVIEWER`, `IMPROVER`) দিলে শুধু ওই এজেন্ট অন্য মডেলে চলে। যেমন বিচারক (Reviewer) আলাদা মডেলে, যাতে নিজের কাজ নিজে বিচার না করে:

```
export PROVIDER=groq MODEL=openai/gpt-oss-20b
export MODEL_REVIEWER=qwen/qwen3.8-27b          # একই Groq key, আলাদা মডেল
export PROVIDER_REVIEWER=gemini                  # অথবা অন্য প্রোভাইডার (GEMINI_API_KEY লাগবে)
```

Groq-এ প্রতিটা মডেলের দৈনিক সীমা আলাদা। তবে টোকেনের বেশিরভাগ যায় Worker-এ, তাই শুধু Reviewer সরালে সীমা সামান্যই বাঁচে। ভূমিকা-ম্যাপিং রান জুড়ে স্থির থাকে (নিজে নিজে অন্য মডেলে সরে না), কারণ মাঝপথে মডেল বদলালে eval-এর স্কোর মেলানো যায় না। কনফিগারেশন বদলালে নতুন বেসলাইন নিন।

`eval`-এ ১৩টা কাজ আছে (`evals/tasks.json`)। চেকগুলো কোড দিয়ে হয়, উত্তরের অর্থ বোঝে না: দরকারি শব্দ আছে কি না (`must_contain`), শব্দসংখ্যার সীমা (`max_words`), আর কত টুকরোয় (ফাঁকা লাইন দিয়ে আলাদা অনুচ্ছেদ) ভাঙা (`max_paragraphs`)। শেষটা ধরে সহজ প্রশ্ন অকারণে কয়েক ধাপে ভেঙে টুকরো-টুকরো উত্তর দেওয়ার সমস্যা।

## ব্রাউজার চ্যাট পেজ

Termux-এ বাংলা ভাঙা দেখায়, তাই ফোনের Chrome-এ চ্যাট পেজ আছে (সার্ভার ফোনেই চলে, বাইরে কিছু যায় না):

```
export PYTHONPATH=src
export ECOSYSTEM_API_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(24))")
export ECOSYSTEM_OWNER_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(24))")
# (এর আগে মডেলের PROVIDER ও key export করা থাকতে হবে)
python -m ecosystem serve --port 8765
```

নতুন Termux সেশনে `echo $ECOSYSTEM_API_TOKEN` দিয়ে টোকেন দেখুন (আগের সেশনের টোকেন হারিয়ে যায়, নতুন বানাতে হয়)। Chrome-এ `http://127.0.0.1:8765` খুলে সেই টোকেন দিন। পেজে কথা বলা, প্রস্তাব দেখা, ⛔ Kill, আর Owner টোকেন দিয়ে অনুমোদন/Kill তোলা যায়। প্রতিটা বার্তা আলাদা কাজ, আগের কথা মনে রাখে না। পেজে provider-এর key দেওয়া যায় না, সেটা Termux-এ export করতে হয়।

## HTTP API

দুটো আলাদা টোকেন লাগে (১৬+ অক্ষর), না থাকলে সার্ভার চালুই হয় না:

```
export ECOSYSTEM_API_TOKEN=...      # user: run, eval, improve, test, kill
export ECOSYSTEM_OWNER_TOKEN=...    # owner: সব, সঙ্গে approve, resume, audit
python -m ecosystem serve --port 8765      # ডিফল্ট শুধু 127.0.0.1
```

| Method | পথ | কে পারে |
|---|---|---|
| GET | `/health` | যে কেউ |
| GET | `/status`, `/proposals`, `/proposals/{id}` | user, owner |
| POST | `/run` `{"task": "..."}` | user, owner |
| POST | `/eval`, `/improve`, `/proposals/{id}/test` | user, owner |
| POST | `/kill` | user, owner (বন্ধ করা সবার জন্য খোলা) |
| POST | `/resume` | শুধু owner |
| POST | `/proposals/{id}/approve` `{"confirm": true}` | শুধু owner |
| GET | `/audit?n=50` | শুধু owner |

```
curl -H "Authorization: Bearer $ECOSYSTEM_API_TOKEN" -X POST \
     -d '{"task":"..."}' http://127.0.0.1:8765/run
```

একসাথে একটাই মডেল-কাজ চলে (অন্যটা এলে 409)। Owner টোকেন এজেন্টদের হাতে দেবেন না। সার্ভার সাধারণ HTTP, লোকালহোস্টের বাইরে দিলে TLS reverse proxy লাগবে।

## টেস্ট

```
PYTHONPATH=src python -m unittest discover -s tests
```

## অবস্থা

- Mock মডেলে সব নিয়ন্ত্রণ-অংশ (kill switch, বাজেট, অনুমোদন) টেস্ট করা।
- Groq আসল API-তে চালানো হয়েছে (`openai/gpt-oss-20b`, ৩টা কাজের পুরনো eval)। Ollama ও Gemini এখনো আসল সার্ভারে চালানো হয়নি।
- ১৩ কাজের নতুন eval আসল মডেলে এখনো চালানো হয়নি, তাই এর বেসলাইন স্কোর অজানা।
- HTTP API mock মডেলে টেস্ট করা (টোকেন, অনুমতি, kill switch, approve)। আসল মডেল দিয়ে এখনো চালানো হয়নি, আর দীর্ঘ কাজে অনুরোধ সিঙ্ক্রোনাস, তাই সময়সীমা পেরোতে পারে (পরে job queue দরকার হতে পারে)।
