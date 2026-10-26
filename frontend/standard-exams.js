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
      publish.onclick=async()=>{try{await request("/api/standard/publish/"+encodeURIComponent(d.id),{method:"POST"});publish.textContent="Published";publish.disabled=true;document.getElementById("std-builder-refresh")?.click()}catch(e){alert(e.message)}};
      row.append(title,publish);drafts.append(row);
    }}catch(e){drafts.textContent=e.message}
  };
  const panel=document.createElement("section");panel.className="panel";panel.id="standard-exams";
  const heading=document.createElement("h3");heading.textContent="Required exam / الامتحان المحدد من المدير";
  const load=document.createElement("button");load.className="primary";load.textContent="Refresh assigned exam / تحديث الامتحان";
  const content=document.createElement("div");panel.append(heading,load,content);area.prepend(panel);
  document.addEventListener("tso:student-login",()=>load.click());
  if(!area.classList.contains('hidden'))queueMicrotask(()=>load.click());
  load.onclick=async()=>{
    content.replaceChildren();
    try{const exams=await request("/api/standard/exams");if(!exams.length){content.textContent="No required exam assigned to your grade yet / لم يحدد المدير امتحانًا لصفك بعد.";return}
      const exam=exams[0];
      const label=document.createElement("p");label.textContent="Assigned by your teacher / امتحان محدد من المدير: "+exam.title+" ("+exam.question_count+" questions)";
      const b=document.createElement("button");b.className="primary";b.textContent="Start required exam / ابدأ الامتحان الإجباري";b.onclick=()=>start(exam.id);
      content.append(label,b);
    }catch(e){content.textContent=e.message}
  };
  const practice=document.createElement("section");practice.className="panel";
  practice.innerHTML='<h3>Custom Practice / تدريب حسب اختيارك</h3><p>Choose units and question types from your own grade.</p><div id="std-practice-filters"></div><label>Questions <select id="std-practice-count"><option selected>20</option><option>40</option><option>60</option><option>80</option><option>100</option></select></label><button class="primary" id="std-practice-start">Start custom practice</button><p id="std-practice-status" role="status"></p>';
  area.prepend(practice);
  practice.classList.add("hidden"); // Student practice is disabled: only the assigned official exam is available.
  const filterBox=practice.querySelector("#std-practice-filters"),practiceStatus=practice.querySelector("#std-practice-status");
  const selected=key=>[...filterBox.querySelectorAll('input[data-group="'+key+'"]:checked')].map(el=>el.value);
  async function loadPracticeFilters(){
    try{
      const data=await request("/api/standard/practice-filters");filterBox.replaceChildren();
      const title=document.createElement("p");title.textContent="Your grade: "+data.grade;filterBox.append(title);
      for(const [group,key] of [["unit","unit"],["kind","kind"]]){
        const section=document.createElement("div");const heading=document.createElement("strong");heading.textContent=group==="unit"?"Units: ":"Question types: ";section.append(heading);
        for(const value of [...new Set(data.filters.map(x=>x[key]))]){
          const label=document.createElement("label");label.style.margin="8px";const cb=document.createElement("input");cb.type="checkbox";cb.dataset.group=group;cb.value=value;label.append(cb,document.createTextNode(" "+value));section.append(label)
        }filterBox.append(section)
      }
    }catch(e){practiceStatus.textContent=e.message}
  }
  practice.querySelector("#std-practice-start").onclick=async()=>{
    const units=selected("unit"),kinds=selected("kind"),count=Number(practice.querySelector("#std-practice-count").value);
    if(!units.length||!kinds.length){practiceStatus.textContent="Select units and question types first.";return}
    try{
      const result=await request("/api/standard/practice-create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({units,kinds,count})});
      await start("practice:"+result.id);
    }catch(e){practiceStatus.textContent=e.message}
  };
  document.addEventListener('tso:student-login',loadPracticeFilters);
  if(!document.getElementById('student-area').classList.contains('hidden'))loadPracticeFilters();
  async function start(id){
    content.replaceChildren();
    try{
      const exam=await request((id.startsWith("practice:")?"/api/standard/practice/":"/api/standard/exams/")+encodeURIComponent(id.replace(/^practice:/,"")));
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
          try{const result=await request((id.startsWith("practice:")?"/api/standard/practice/":"/api/standard/exams/")+encodeURIComponent(id.replace(/^practice:/,""))+"/submit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({attempt_id:attemptId,answers})});content.textContent="Your result: "+result.score+" / "+result.maximum; if(typeof loadResults==="function")loadResults();}
          catch(e){next.disabled=false;alert(e.message)}
        };nav.append(next);content.append(nav);
      };render();
    }catch(e){content.textContent=e.message}
  }
});
