"""The browser chat page (one self-contained file, no external scripts or fonts).
It holds no secrets: the user types the API token into it. Model output is always inserted with
textContent, never innerHTML, so an answer cannot inject markup into the page."""

PAGE = r"""<!doctype html>
<html lang="bn"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iCell-AI</title>
<style>
:root{--bg:#0f1420;--card:#1a2233;--text:#e8ecf4;--mute:#93a0b8;--acc:#4f8cff;--red:#e5484d;--ok:#3fb27f;--line:#2a3550}
@media (prefers-color-scheme: light){:root{--bg:#f4f6fb;--card:#fff;--text:#18202f;--mute:#5b6980;--line:#d9dfec}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,"Noto Sans Bengali","Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;display:flex;gap:8px;align-items:center;padding:10px 16px;background:var(--card);border-bottom:1px solid var(--line)}
header h1{font-size:17px;margin:0;flex:1}
#state{font-size:12px;color:var(--mute)}
button{font:inherit;border:0;border-radius:10px;padding:10px 14px;background:var(--acc);color:#fff;cursor:pointer}
button.kill{background:var(--red);font-weight:700}
button.ghost{background:transparent;color:var(--acc);border:1px solid var(--line)}
button:disabled{opacity:.5}
main{max-width:720px;margin:0 auto;padding:12px 16px 120px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:10px 0}
.you{background:var(--acc);color:#fff;border:0;margin-left:36px}
.bot{margin-right:12px}
.meta{font-size:13px;color:var(--mute);margin-top:8px}
.err{border-color:var(--red);color:var(--red)}
pre{white-space:pre-wrap;word-wrap:break-word;margin:0;font:inherit}
details{margin-top:8px;font-size:14px;color:var(--mute)}
input,textarea{width:100%;font:inherit;padding:10px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--text)}
nav{display:flex;gap:8px;margin:8px 0}
nav button{flex:1;background:var(--card);color:var(--text);border:1px solid var(--line)}
nav button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
#composer{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 16px}
#composer div{max-width:720px;margin:0 auto;display:flex;gap:8px}
#composer textarea{height:48px;resize:none}
.hide{display:none}
.row{display:flex;gap:8px;margin-top:8px}
small{color:var(--mute)}
</style></head><body>
<header><h1>iCell-AI</h1><span id="state">সংযুক্ত নয়</span><button class="kill" id="kill">⛔ Kill</button></header>
<main>
<div id="login" class="card">
  <b>সংযোগ</b><br><small>Termux-এ <code>echo $ECOSYSTEM_API_TOKEN</code> দিলে যে টোকেন আসে সেটা এখানে দিন।</small>
  <div class="row"><input id="tok" type="password" placeholder="API token" autocomplete="off"><button id="go">সংযোগ</button></div>
</div>
<nav id="tabs" class="hide"><button id="t1" class="on">কথা</button><button id="t2">প্রস্তাব</button></nav>
<section id="chat" class="hide"><div id="log"></div>
<p><small>প্রতিটা বার্তা আলাদা কাজ, আগের কথা মনে রাখে না। একসাথে একটাই কাজ চলে।</small></p></section>
<section id="props" class="hide">
  <div class="row"><button class="ghost" id="reload">রিফ্রেশ</button></div>
  <div id="plist"></div>
  <div class="card"><b>Owner (অনুমোদন / Kill তোলা)</b><br><small>Termux-এ <code>echo $ECOSYSTEM_OWNER_TOKEN</code>। এজেন্টদের হাতে এটা দেবেন না।</small>
    <input id="otok" type="password" placeholder="Owner token" autocomplete="off" style="margin-top:8px">
    <div class="row"><button class="ghost" id="resume">Kill তুলুন</button></div></div>
</section>
</main>
<div id="composer" class="hide"><div><textarea id="msg" placeholder="আপনার কাজ বা প্রশ্ন"></textarea><button id="send">পাঠান</button></div></div>
<script>
"use strict";
const $=id=>document.getElementById(id);
let TOK=""; try{TOK=sessionStorage.getItem("tok")||"";}catch(e){}
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
async function api(method,path,body,token){
  const r=await fetch(path,{method,headers:{"Authorization":"Bearer "+(token||TOK),"Content-Type":"application/json"},
    body:method==="POST"?JSON.stringify(body||{}):undefined});
  let data={};try{data=await r.json();}catch(e){}
  if(!r.ok){const e=new Error(data.error||("HTTP "+r.status));e.code=r.status;throw e;}
  return data;
}
function setState(s){$("state").textContent=(s.killed?"⛔ STOP চালু · ":"চালু · ")+s.provider;}
async function refreshState(){try{setState(await api("GET","/status"));}catch(e){$("state").textContent="সংযুক্ত নয়";}}
async function connect(){
  TOK=$("tok").value.trim()||TOK;
  try{const s=await api("GET","/status");setState(s);try{sessionStorage.setItem("tok",TOK);}catch(e){}
    $("login").classList.add("hide");["tabs","chat","composer"].forEach(i=>$(i).classList.remove("hide"));$("tok").value="";}
  catch(e){alert(e.code===401?"টোকেন ভুল":("সংযোগ হয়নি: "+e.message));}
}
function addMsg(node){$("log").appendChild(node);node.scrollIntoView({block:"end"});}
async function send(){
  const t=$("msg").value.trim();if(!t)return;
  $("msg").value="";$("send").disabled=true;
  addMsg(el("div","card you",t));
  const wait=el("div","card bot","চলছে… (কয়েক সেকেন্ড থেকে এক-দুই মিনিট)");addMsg(wait);
  try{
    const r=await api("POST","/run",{task:t});
    const c=el("div","card bot");c.appendChild(el("pre","",r.answer));
    c.appendChild(el("div","meta","রিভিউয়ার: "+r.score+"/10 — "+r.feedback));
    const d=el("details");d.appendChild(el("summary","","প্ল্যান ("+r.plan.length+" ধাপ)"));
    d.appendChild(el("pre","",r.plan.map((s,i)=>(i+1)+". "+s).join("\n")));c.appendChild(d);
    wait.replaceWith(c);
  }catch(e){
    const msg=e.code===503?"⛔ Kill switch চালু, কাজ থামানো।":e.code===409?"অন্য কাজ চলছে, একটু পরে চেষ্টা করুন।":("ত্রুটি: "+e.message);
    const c=el("div","card bot err",msg);wait.replaceWith(c);
  }
  $("send").disabled=false;refreshState();
}
async function loadProps(){
  const box=$("plist");box.textContent="";
  try{const r=await api("GET","/proposals");
    if(!r.proposals.length)box.appendChild(el("div","card","কোনো প্রস্তাব নেই।"));
    r.proposals.forEach(p=>{
      const c=el("div","card");c.appendChild(el("b","","#"+p.id+" ["+p.status+"] "+p.target));
      c.appendChild(el("div","meta",p.reason));
      const d=el("details");d.appendChild(el("summary","","নতুন প্রম্পট"));d.appendChild(el("pre","",p.new_prompt));c.appendChild(d);
      if(p.status==="pending"){const b=el("button","","অনুমোদন (Owner)");b.style.marginTop="10px";
        b.onclick=()=>approve(p);c.appendChild(b);}
      box.appendChild(c);});
  }catch(e){box.appendChild(el("div","card err","ত্রুটি: "+e.message));}
}
async function approve(p){
  const ot=$("otok").value.trim();if(!ot){alert("নিচে Owner token দিন");return;}
  if(!confirm("প্রম্পট বদলাবে ("+p.target+"):\n\n"+p.new_prompt.slice(0,600)+"\n\nঅনুমোদন দিচ্ছেন?"))return;
  try{await api("POST","/proposals/"+p.id+"/approve",{confirm:true},ot);alert("প্রয়োগ হয়েছে");}
  catch(e){alert("হয়নি: "+e.message);}loadProps();
}
function tab(n){$("chat").classList.toggle("hide",n!==1);$("composer").classList.toggle("hide",n!==1);
  $("props").classList.toggle("hide",n!==2);$("t1").classList.toggle("on",n===1);$("t2").classList.toggle("on",n===2);if(n===2)loadProps();}
$("go").onclick=connect;$("send").onclick=send;$("t1").onclick=()=>tab(1);$("t2").onclick=()=>tab(2);$("reload").onclick=loadProps;
$("kill").onclick=async()=>{try{await api("POST","/kill");}catch(e){alert("Kill করা যায়নি: "+e.message);}refreshState();};
$("resume").onclick=async()=>{const ot=$("otok").value.trim();if(!ot){alert("Owner token দিন");return;}
  try{await api("POST","/resume",{},ot);}catch(e){alert("হয়নি: "+e.message);}refreshState();};
if(TOK){$("tok").value=TOK;connect();}
</script></body></html>
"""
