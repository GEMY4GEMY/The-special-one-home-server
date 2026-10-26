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
      const exam=await request("/api/standard/exams/"+encodeURIComponent(id));
      const answers={};
      const pageSize=6;
      let page=0;
      const attemptId=crypto.randomUUID?crypto.randomUUID():String(Date.now())+"-attempt";
      const totalPages=Math.ceil(exam.questions.length/pageSize);
      const render=()=>{
        content.replaceChildren();
        const paper=document.createElement("article");paper.className="tso-exam-paper";
        const header=document.createElement("header");header.className="tso-paper-header";
        const logo=document.createElement("div");logo.className="tso-paper-logo";logo.textContent="★ THE SPECIAL ONE";
        const subtitle=document.createElement("div");subtitle.textContent="Sponsored by Mr. Sameh Abdel Hafeez";
        const heading=document.createElement("h2");heading.textContent=exam.title;
        const meta=document.createElement("div");meta.className="tso-paper-meta";meta.textContent="Official exam • Page "+(page+1)+" / "+totalPages+" • "+exam.questions.length+" questions";
        header.append(logo,subtitle,heading,meta);paper.append(header);
        const list=document.createElement("div");list.className="tso-paper-questions";
        exam.questions.slice(page*pageSize,(page+1)*pageSize).forEach((q,i)=>{
          const item=document.createElement("section");item.className="tso-paper-question";
          const prompt=document.createElement("div");prompt.className="tso-paper-prompt";
          const number=document.createElement("span");number.className="tso-question-number";number.textContent=String(page*pageSize+i+1);
          const text=document.createElement("span");const imageMarker="\n[[image:";const markerIndex=q.prompt.lastIndexOf(imageMarker);const imagePath=markerIndex>=0&&q.prompt.endsWith("]]")?q.prompt.slice(markerIndex+imageMarker.length,-2):"";const imageMatch=/^\/static\/[A-Za-z0-9_./-]+$/.test(imagePath)?imagePath:null;text.textContent=imageMatch?q.prompt.slice(0,markerIndex):q.prompt;
          prompt.append(number,text);item.append(prompt);
          if(imageMatch){const img=document.createElement("img");img.src=imageMatch;img.alt="Question illustration / صورة السؤال";img.loading="lazy";img.style.cssText="display:block;max-width:100%;max-height:180px;object-fit:contain;margin:12px auto;border-radius:10px";item.append(img)}
          const choices=document.createElement("div");choices.className="tso-paper-choices";
          if(q.type==="choose"){
            q.options.forEach((option,n)=>{
              const label=document.createElement("label");label.className="tso-paper-option";
              const input=document.createElement("input");input.type="radio";input.name="answer-"+q.id;input.value=option;input.checked=answers[q.id]===option;
              input.onchange=()=>{answers[q.id]=option};
              const letter=document.createElement("strong");letter.textContent=String.fromCharCode(65+n)+".";
              const span=document.createElement("span");span.textContent=option;
              label.append(input,letter,span);choices.append(label);
            });
          }else{
            const field=document.createElement("input");field.type="text";field.className="tso-written-answer";field.placeholder=q.type==="rearrange"?"Write the correct sentence / رتب الجملة":"Write your answer / اكتب الإجابة";field.value=answers[q.id]||"";
            field.oninput=()=>{answers[q.id]=field.value};choices.append(field);
          }
          item.append(choices);list.append(item);
        });
        paper.append(list);
        const footer=document.createElement("footer");footer.className="tso-paper-footer";footer.textContent="Do your best! 🌟  •  THE SPECIAL ONE";paper.append(footer);
        content.append(paper);
        const nav=document.createElement("nav");nav.className="tso-paper-nav";
        const indicator=document.createElement("span");indicator.textContent="Page "+(page+1)+" of "+totalPages+" • Answered "+Object.keys(answers).filter(k=>answers[k]?.trim()).length+"/"+exam.questions.length;
        const previous=document.createElement("button");previous.className="outline";previous.textContent="← Previous page";previous.disabled=page===0;previous.onclick=()=>{page--;render();paper.scrollIntoView({behavior:"smooth",block:"start"})};
        const next=document.createElement("button");next.className="primary";next.textContent=page===totalPages-1?"Finish exam / إنهاء الامتحان":"Next page →";
        next.onclick=async()=>{
          if(page<totalPages-1){page++;render();content.scrollIntoView({behavior:"smooth",block:"start"});return}
          if(!confirm("Finish and submit your exam? / هل تريد إنهاء الامتحان وتسليمه؟"))return;
          next.disabled=true;
          try{
            const result=await request("/api/standard/exams/"+encodeURIComponent(id)+"/submit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({attempt_id:attemptId,answers})});
            content.replaceChildren();
            const score=document.createElement("section");score.className="tso-exam-result";score.textContent="🌟 Your result / نتيجتك: "+result.score+" / "+result.maximum;content.append(score);
            if(typeof loadResults==="function")loadResults();
          }catch(e){next.disabled=false;alert(e.message)}
        };
        nav.append(previous,indicator,next);content.append(nav);
      };
      render();
    }catch(e){content.textContent=e.message}
  }
});
