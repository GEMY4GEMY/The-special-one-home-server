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
  if(me.role==='student'){loadResults();document.dispatchEvent(new Event('tso:student-login'));}
}
async function loadResults(){
  const area=$('results');
  area.replaceChildren();
  try{
    const results=(await api('/api/standard/my-attempts')).map(x=>({exam_title:'Published exam',score:x.score,maximum:x.maximum,created_at:x.submitted_at}));
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

let examState=null;
function make(tag, text, className){
  const node=document.createElement(tag);
  if(text!==undefined)node.textContent=text;
  if(className)node.className=className;
  return node;
}
async function setupDemoExam(){
  if($('exam-area'))return;
  const panel=make('section',undefined,'panel');
  panel.id='exam-area';
  panel.style.marginTop='20px';
  panel.append(make('h3','Practice Exam — Demo 📝'));
  panel.append(make('p','Illustrative questions only. Not sourced from curriculum files.'));
  const start=make('button','Start demo exam →','primary');
  start.type='button';start.addEventListener('click',startDemoExam);
  panel.append(start);
  $('student-area').append(panel);
}
async function startDemoExam(){
  const panel=$('exam-area');
  try{
    const exam=await api('/api/exams/demo-english-001');
    examState={exam,answers:{},index:0,attemptId:crypto.randomUUID()};
    renderDemoQuestion();
  }catch{panel.append(make('p','Cannot load exam. Check the server connection.','error'));}
}
function renderDemoQuestion(){
  const {exam,index,answers}=examState;
  const q=exam.questions[index],panel=$('exam-area');
  panel.replaceChildren(make('h3',exam.title),make('p','Question '+(index+1)+' of '+exam.questions.length));
  const bar=make('div',undefined,'progress-bar');
  const fill=make('div',undefined,'progress-fill');fill.style.width=(100*(index+1)/exam.questions.length)+'%';bar.append(fill);panel.append(bar);
  panel.append(make('h3',q.prompt));
  const options=make('div',undefined,'answer-options');
  if(q.type==='choose'){
    for(const value of q.options){
      const btn=make('button',value,'answer-option'+(answers[q.id]===value?' selected':''));
      btn.type='button';btn.addEventListener('click',()=>{answers[q.id]=value;renderDemoQuestion()});options.append(btn);
    }
  }else{
    const input=make('input');
    input.type='text';input.autocomplete='off';input.placeholder=q.type==='rearrange'?'Write the correct sentence':'Type your answer';
    input.value=answers[q.id]||'';
    input.setAttribute('aria-label','Your answer');
    input.addEventListener('input',()=>{answers[q.id]=input.value});
    options.append(input);
  }
  panel.append(options);
  const nav=make('div',undefined,'exam-nav');
  if(index>0){const prev=make('button','← Previous','outline');prev.type='button';prev.addEventListener('click',()=>{examState.index--;renderDemoQuestion()});nav.append(prev);}
  const next=make('button',index===exam.questions.length-1?'Submit answers ✓':'Next →','primary');
  next.type='button';next.addEventListener('click',()=>{if(examState.index<exam.questions.length-1){examState.index++;renderDemoQuestion()}else submitDemoExam()});nav.append(next);
  panel.append(nav);
}
async function submitDemoExam(){
  const panel=$('exam-area'),state=examState;
  if(!state)return;
  const data={attempt_id:state.attemptId,answers:Object.entries(state.answers).map(([question_id,answer])=>({question_id,answer}))};
  const buttons=panel.querySelectorAll('button');buttons.forEach(b=>b.disabled=true);
  try{
    const result=await api('/api/exams/'+state.exam.id+'/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    panel.replaceChildren(make('h2','Great effort! 🌟'),make('p','Your demo score: '+result.score+' / '+result.maximum));
    const again=make('button','Try another demo','primary');again.addEventListener('click',startDemoExam);panel.append(again);
    examState=null;
  }catch{
    buttons.forEach(b=>b.disabled=false);
    panel.append(make('p','Submission failed. Keep this page open and retry when the connection returns.','error'));
    const retry=make('button','Retry submission','outline');retry.addEventListener('click',submitDemoExam);panel.append(retry);
  }
}
