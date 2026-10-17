"use strict";
const $ = id => document.getElementById(id);
let lastOnline = null;
async function checkConnection(){
  try {
    const r=await fetch('/health',{cache:'no-store',signal:AbortSignal.timeout(4000)});
    setNetwork(r.ok);
  } catch { setNetwork(false); }
}
function setNetwork(online){
  if(lastOnline===online)return;
  lastOnline=online;
  $('network').textContent=online?'● Server connected':'● Connection lost';
  $('network').classList.toggle('offline',!online);
}
async function api(path, options={}){
  const r=await fetch(path,{credentials:'same-origin',...options});
  if(!r.ok)throw new Error('Request failed ('+r.status+')');
  return r.json();
}
function showDashboard(me){
  $('login-panel').classList.add('hidden');
  $('dashboard').classList.remove('hidden');
  $('welcome-title').textContent='Hello, '+me.username+'!';
  $('welcome-subtitle').textContent=me.role==='student'?'Your results are private and ready to explore.':'Your administration workspace.';
  $('student-area').classList.toggle('hidden',me.role!=='student');
  $('admin-area').classList.toggle('hidden',me.role!=='admin');
  if(me.role==='student')loadResults();
}
async function loadResults(){
  const area=$('results');
  area.replaceChildren();
  try{
    const results=await api('/api/my-results');
    $('completed').textContent=String(results.length);
    const avg=results.length?results.reduce((sum,r)=>sum+100*r.score/r.maximum,0)/results.length:null;
    $('average').textContent=avg===null?'—':Math.round(avg)+'%';
    if(!results.length){const p=document.createElement('p');p.textContent='No published results yet.';area.append(p);return;}
    for(const result of results){
      const row=document.createElement('div');row.className='result-item';
      const title=document.createElement('span');title.textContent=result.exam_title;
      const score=document.createElement('strong');score.textContent=result.score+' / '+result.maximum;
      row.append(title,score);area.append(row);
    }
  }catch{const p=document.createElement('p');p.textContent='Results are temporarily unavailable. Please reconnect.';area.append(p);}
}
$('login-form').addEventListener('submit',async e=>{
  e.preventDefault();
  $('login-error').textContent='';
  const button=e.currentTarget.querySelector('button');button.disabled=true;
  try{
    const me=await api('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:$('username').value,password:$('password').value})});
    showDashboard(me);
  }catch{$('login-error').textContent='Could not sign in. Check your details and connection.';}
  finally{button.disabled=false;}
});
$('logout').addEventListener('click',async()=>{
  try{await api('/api/logout',{method:'POST'});}catch{}
  location.reload();
});
async function restoreSession(){try{showDashboard(await api('/api/me'));}catch{}}
window.addEventListener('online',checkConnection);
window.addEventListener('offline',()=>setNetwork(false));
checkConnection();restoreSession();setInterval(checkConnection,5000);
