"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const area=document.getElementById("student-area");
  const admin=document.getElementById("admin-area");
  if(!area||!admin)return;
  const adminPanel=document.createElement("section");adminPanel.className="panel admin-panel";
  adminPanel.innerHTML='<h3>Publish exam drafts / نشر الامتحانات</h3><button type="button" class="outline" id="std-load-drafts">Refresh drafts</button><div id="std-drafts"></div>';
  admin.prepend(adminPanel);
  const request=async(url,options={})=>{const r=await fetch(url,{credentials:"same-origin",...options});const data=await r.json();if(!r.ok)throw Error(data.detail||"Request failed");return data};
  const drafts=document.getElementById("std-drafts");
  document.getElementById("std-load-drafts").onclick=async()=>{
    drafts.replaceChildren();
    try{for(const d of await request("/api/admin/exam-drafts")){
      const row=document.createElement("div");row.className="result-item";
      const title=document.createElement("span");title.textContent=d.title+" | "+d.grade+" | "+d.question_count;
      const publish=document.createElement("button");publish.textContent="Publish";publish.className="outline";
      publish.onclick=async()=>{try{await request("/api/standard/publish/"+encodeURIComponent(d.id),{method:"POST"});publish.textContent="Published";publish.disabled=true}catch(e){alert(e.message)}};
      row.append(title,publish);drafts.append(row);
    }}catch(e){drafts.textContent=e.message}
  };
  const panel=document.createElement("section");panel.className="panel";panel.id="standard-exams";
  const heading=document.createElement("h3");heading.textContent="My published exams / امتحاناتي";
  const load=document.createElement("button");load.className="primary";load.textContent="Load my exams";
  const content=document.createElement("div");panel.append(heading,load,content);area.prepend(panel);
  load.onclick=async()=>{
    content.replaceChildren();
    try{const exams=await request("/api/standard/exams");if(!exams.length){content.textContent="No published exams for your grade yet.";return}
      for(const exam of exams){const b=document.createElement("button");b.className="outline";b.textContent=exam.title+" ("+exam.question_count+" questions)";b.onclick=()=>start(exam.id);content.append(b)}
    }catch(e){content.textContent=e.message}
  };
  async function start(id){
    content.replaceChildren();
    try{
      const exam=await request("/api/standard/exams/"+encodeURIComponent(id));
      const answers={};let index=0;const attemptId=(crypto.randomUUID?crypto.randomUUID():String(Date.now())+"-attempt");
      const render=()=>{
        content.replaceChildren();
        const q=exam.questions[index],title=document.createElement("h3");title.textContent="Question "+(index+1)+"/"+exam.questions.length+": "+q.prompt;content.append(title);
        if(q.type==="choose"){for(const option of q.options){const b=document.createElement("button");b.className="outline";b.textContent=option;b.onclick=()=>{answers[q.id]=option;render()};if(answers[q.id]===option)b.setAttribute("aria-pressed","true");content.append(b)}}
        else{const field=document.createElement("input");field.placeholder="Write your answer";field.value=answers[q.id]||"";field.oninput=()=>answers[q.id]=field.value;content.append(field)}
        const nav=document.createElement("div");nav.className="exam-nav";
        if(index>0){const prev=document.createElement("button");prev.textContent="Previous";prev.onclick=()=>{index--;render()};nav.append(prev)}
        const next=document.createElement("button");next.className="primary";next.textContent=index===exam.questions.length-1?"Finish and see result":"Next";
        next.onclick=async()=>{if(index<exam.questions.length-1){index++;render();return}
          if(!confirm("Finish exam and submit your answers?"))return;
          next.disabled=true;
          try{const result=await request("/api/standard/exams/"+encodeURIComponent(id)+"/submit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({attempt_id:attemptId,answers})});content.textContent="Your result: "+result.score+" / "+result.maximum;}
          catch(e){next.disabled=false;alert(e.message)}
        };nav.append(next);content.append(nav);
      };render();
    }catch(e){content.textContent=e.message}
  }
});
