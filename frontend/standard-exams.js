"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const area=document.getElementById("student-area");
  const admin=document.getElementById("admin-area");
  if(!area||!admin)return;
  const panel=document.createElement("section");panel.className="panel";panel.id="standard-exams";
  const heading=document.createElement("h3");heading.textContent="Required exam / الامتحان المحدد من المدير";
  const load=document.createElement("button");load.className="primary";load.textContent="Refresh assigned exam / تحديث الامتحان";
  const content=document.createElement("div");panel.append(heading,load,content);area.prepend(panel);
  document.addEventListener("tso:student-login",()=>load.click());
  if(!area.classList.contains('hidden'))queueMicrotask(()=>load.click());
  load.onclick=async()=>{
    content.replaceChildren();
    panel.querySelector("#tso-conflict-comparison")?.remove();
    try{const exams=await request("/api/standard/exams");if(!exams.length){content.textContent="No current exam assigned / لا يوجد امتحان منشور حاليًا.";}
      const exam=exams[0];
      if(exam){
      const label=document.createElement("p");label.textContent="Assigned by your teacher / امتحان محدد من المدير: "+exam.title+" ("+exam.question_count+" questions)";
      const b=document.createElement("button");b.className="primary";let saved=false;try{saved=Object.keys(sessionStorage).some(key=>key.startsWith("tso-exam-progress:")&&key.endsWith(":"+exam.id))}catch(_){}b.textContent=saved?"Continue exam / استكمال الامتحان":"Start required exam / ابدأ الامتحان الإجباري";b.onclick=()=>start(exam.id);
      content.append(label,b);
      }
      const resumable=await request("/api/standard/resumable-exams");
      for(const pending of resumable.filter(x=>!exam||x.id!==exam.id)){
        const resume=document.createElement("button");resume.className="outline";
        resume.textContent="Continue previous exam / استكمال الامتحان السابق: "+pending.title;
        resume.onclick=()=>start(pending.id);content.append(resume);
      }
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
  const saveStatus=document.createElement("p");
  saveStatus.className="muted";
  saveStatus.setAttribute("role","status");
  saveStatus.setAttribute("aria-live","polite");
  panel.insertBefore(saveStatus,content);
  let stopPreviousProgressListeners=null;
  document.addEventListener("tso:student-logout",()=>{
    if(stopPreviousProgressListeners){
      stopPreviousProgressListeners();
      stopPreviousProgressListeners=null;
    }
    saveStatus.textContent="";
    content.replaceChildren();
  });
  async function start(id){
    if(stopPreviousProgressListeners){
      stopPreviousProgressListeners();
      stopPreviousProgressListeners=null;
    }
    content.replaceChildren();
    saveStatus.textContent="Loading exam / جاري تحميل الامتحان";
    try{
      const exam=await request("/api/standard/exams/"+encodeURIComponent(id));
      const storageKey="tso-exam-progress:"+id;
      let saved=null;
      try{saved=JSON.parse(sessionStorage.getItem(storageKey)||"null")}catch(_){}
      try{
        const remote=await request("/api/standard/exams/"+encodeURIComponent(id)+"/progress");
        if(remote&&remote.attemptId){
          const localRevision=Number.isSafeInteger(saved?.revision)?saved.revision:0;
          const remoteRevision=Number.isSafeInteger(remote.revision)?remote.revision:0;
          // Server owns the active attempt. Prefer newer local edits only for that same attempt.
          if(!saved||saved.attemptId!==remote.attemptId||remoteRevision>=localRevision) saved=remote;
        }
      }catch(error){console.warn("Server progress unavailable; using local recovery",error)}
      // A conflict backup is never merged automatically into the server attempt.
      // Show it explicitly so the student can preserve their unsynced work.
      let conflictBackup=null;
      try{conflictBackup=JSON.parse(sessionStorage.getItem(storageKey+":conflict-backup")||"null")}catch(_){}
      if(conflictBackup && typeof conflictBackup.answers==="object" && conflictBackup.answers){
        const backupAnswers=conflictBackup.answers;
        const serverAnswers=saved&&typeof saved.answers==="object"&&saved.answers?saved.answers:{};
        const allIds=new Set([...Object.keys(backupAnswers),...Object.keys(serverAnswers)]);
        let differing=0;
        for(const qid of allIds) if(backupAnswers[qid]!==serverAnswers[qid]) differing++;
        const comparison=document.createElement("details");
        const summary=document.createElement("summary");
        summary.textContent="Compare saved answers / مقارنة الإجابات المحفوظة";
        const info=document.createElement("p");
        info.textContent="Local backup: "+Object.keys(backupAnswers).length+" answers; current attempt: "+Object.keys(serverAnswers).length+" answers; differences: "+differing+" / النسخة المحلية: "+Object.keys(backupAnswers).length+"، المحاولة الحالية: "+Object.keys(serverAnswers).length+"، الاختلافات: "+differing+". No automatic merge / لا يوجد دمج تلقائي.";
        comparison.append(summary,info);
        if(differing){
          const differences=document.createElement("ol");
          for(const qid of allIds){
            if(backupAnswers[qid]===serverAnswers[qid]) continue;
            const question=exam.questions.find(q=>String(q.id)===qid);
            const item=document.createElement("li");
            const questionText=document.createElement("strong");
            questionText.textContent=question?.prompt||("Question "+qid+" / السؤال "+qid);
            const local=document.createElement("p");
            local.textContent="Local / محلي: "+(backupAnswers[qid]??"—");
            const remote=document.createElement("p");
            remote.textContent="Current attempt / المحاولة الحالية: "+(serverAnswers[qid]??"—");
            item.append(questionText,local,remote);
            differences.append(item);
          }
          comparison.append(differences);
        }
        const priorComparison=panel.querySelector("#tso-conflict-comparison");
        if(priorComparison) priorComparison.remove();
        comparison.id="tso-conflict-comparison";
        panel.append(comparison);
      }
      const answers=saved&&typeof saved.answers==="object"&&saved.answers? saved.answers:{};
      const pageSize=6;
      let page=Number.isInteger(saved?.page)?Math.max(0,saved.page):0;
      const attemptId=saved?.attemptId||(crypto.randomUUID?crypto.randomUUID():String(Date.now())+"-attempt");
      let revision=Number.isSafeInteger(saved?.revision)?saved.revision:0;
      let saveTimer=null;
      let saveFailureKind=null;
      saveStatus.textContent=conflictBackup&&typeof conflictBackup.answers==="object"&&conflictBackup.answers
        ?"Unsynced local backup available ("+Object.keys(conflictBackup.answers).length+" answers); it is not merged automatically / توجد نسخة محلية غير متزامنة ("+Object.keys(conflictBackup.answers).length+" إجابات) ولم تُدمج تلقائيًا"
        :"Exam ready / الامتحان جاهز";
      const saveProgress=()=>{
        // Preserve the latest local answers until the server confirms this revision.
        saveFailureKind=null;
        saveStatus.textContent="Saving answers / جاري حفظ الإجابات";
        revision+=1;
        try{sessionStorage.setItem(storageKey,JSON.stringify({answers,page,attemptId,revision}))}catch(_){}
        clearTimeout(saveTimer);
        saveTimer=setTimeout(()=>{
          const sentRevision=revision;
          // Snapshot the answers at send time: later edits must not mutate this request.
          const sentAnswers=JSON.parse(JSON.stringify(answers));
          const sentPage=page;
          request("/api/standard/exams/"+encodeURIComponent(id)+"/progress",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({attempt_id:attemptId,answers:sentAnswers,page:sentPage,revision:sentRevision})})
            .then(()=>{if(sentRevision===revision){saveFailureKind=null;saveStatus.textContent="Saved on server / تم الحفظ على السيرفر";}})
             .catch(error=>{
              if(sentRevision!==revision)return;
              const conflict=String(error?.message||"").includes("409");
              saveFailureKind=conflict?"conflict":"offline";
              if(conflict){
                // Preserve the unsynced work separately before the student reloads.
                try{sessionStorage.setItem(storageKey+":conflict-backup",JSON.stringify({answers,page,attemptId,revision}))}catch(_){}
              }
              saveStatus.textContent=conflict
                ?"Save conflict: reopen this exam to load the current attempt / تعارض في الحفظ: افتح الامتحان مجددًا لاسترجاع المحاولة الحالية"
                :"Saved in this browser session; waiting for connection / محفوظ في جلسة المتصفح وفي انتظار الاتصال";
              console.warn("Progress save failed",error);
            });
        },700);
      };
      // Retry the current answers when Wi-Fi returns after an interrupted save.
      const retryOnReconnect=()=>{
        // A 409 is a server-side attempt/revision conflict, not an offline save.
        // Do not retry it automatically: the student must reload the saved attempt.
        if(saveFailureKind==="offline") saveProgress();
      };
      window.addEventListener("online",retryOnReconnect);
      // A tablet may reconnect to the local server without firing the browser online event.
      // Retry only an unsynced save when the student returns to the exam tab.
      const retryOnReturn=()=>{
        if(document.visibilityState==="visible" && saveFailureKind==="offline") saveProgress();
      };
      document.addEventListener("visibilitychange",retryOnReturn);
      // Browsers do not always emit "online" when the local PC server returns.
      // Retry at a modest interval only while the current save is unsynced.
      const retryInterval=setInterval(()=>{
        if(document.visibilityState==="visible" && saveFailureKind==="offline" && navigator.onLine) saveProgress();
      },15000);
      const flushOnPageHide=()=>{
        // A final flush must be newer than any previously queued or completed save.
        revision+=1;
        try{sessionStorage.setItem(storageKey,JSON.stringify({answers,page,attemptId,revision}))}catch(_){}
        clearTimeout(saveTimer);
        fetch("/api/standard/exams/"+encodeURIComponent(id)+"/progress",{
          method:"PUT",credentials:"same-origin",keepalive:true,
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({attempt_id:attemptId,answers,page,revision})
        }).catch(()=>{});
      };
      window.addEventListener("pagehide",flushOnPageHide);
      stopPreviousProgressListeners=()=>{
        window.removeEventListener("online",retryOnReconnect);
        document.removeEventListener("visibilitychange",retryOnReturn);
        clearInterval(retryInterval);
        window.removeEventListener("pagehide",flushOnPageHide);
        clearTimeout(saveTimer);
      };
      const totalPages=Math.ceil(exam.questions.length/pageSize);
      if(saved){const resumed=document.createElement("p");resumed.className="muted";resumed.textContent="Your saved answers were restored / تم استرجاع إجاباتك المحفوظة";content.append(resumed)}
      page=Math.min(page,Math.max(0,totalPages-1));
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
              input.onchange=()=>{answers[q.id]=option;saveProgress()};
              const letter=document.createElement("strong");letter.textContent=String.fromCharCode(65+n)+".";
              const span=document.createElement("span");span.textContent=option;
              label.append(input,letter,span);choices.append(label);
            });
          }else{
            const field=document.createElement("input");field.type="text";field.className="tso-written-answer";field.placeholder=q.type==="rearrange"?"Write the correct sentence / رتب الجملة":"Write your answer / اكتب الإجابة";field.value=answers[q.id]||"";
            field.oninput=()=>{answers[q.id]=field.value;saveProgress()};choices.append(field);
          }
          item.append(choices);list.append(item);
        });
        paper.append(list);
        const footer=document.createElement("footer");footer.className="tso-paper-footer";footer.textContent="Do your best! 🌟  •  THE SPECIAL ONE";paper.append(footer);
        content.append(paper);
        const nav=document.createElement("nav");nav.className="tso-paper-nav";
        const indicator=document.createElement("span");indicator.textContent="Page "+(page+1)+" of "+totalPages+" • Answered "+Object.keys(answers).filter(k=>answers[k]?.trim()).length+"/"+exam.questions.length;
        const previous=document.createElement("button");previous.className="outline";previous.textContent="← Previous page";previous.disabled=page===0;previous.onclick=()=>{page--;saveProgress();render();content.scrollIntoView({behavior:"smooth",block:"start"})};
        const next=document.createElement("button");next.className="primary";next.textContent=page===totalPages-1?"Finish exam / إنهاء الامتحان":"Next page →";
        next.onclick=async()=>{
          if(page<totalPages-1){page++;saveProgress();render();content.scrollIntoView({behavior:"smooth",block:"start"});return}
          if(!confirm("Finish and submit your exam? / هل تريد إنهاء الامتحان وتسليمه؟"))return;
          next.disabled=true;
          try{
            const result=await request("/api/standard/exams/"+encodeURIComponent(id)+"/submit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({attempt_id:attemptId,answers})});
            if(stopPreviousProgressListeners){
              stopPreviousProgressListeners();
              stopPreviousProgressListeners=null;
            }
            saveStatus.textContent="Exam submitted / تم تسليم الامتحان";
            try{sessionStorage.removeItem(storageKey)}catch(_){}
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
