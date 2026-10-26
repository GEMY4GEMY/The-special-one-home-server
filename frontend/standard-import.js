"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const admin=document.getElementById("admin-area");
  if(!admin)return;
  for(const panel of admin.querySelectorAll(".admin-panel")){
    if(panel.querySelector("h3")?.textContent?.includes("AI Question Suggestions"))panel.classList.add("hidden");
  }
  const panel=document.createElement("div");panel.className="panel admin-panel";
  const title=document.createElement("h3");title.textContent="Import question bank / استيراد بنك الأسئلة";
  const description=document.createElement("p");description.className="muted";
  description.textContent="Select an approved JSON question bank. No AI or internet required.";
  const form=document.createElement("form");
  const input=document.createElement("input");input.type="file";input.accept=".json,application/json";input.required=true;
  const stage=document.createElement("select");stage.required=true;stage.innerHTML='<option value="">Select stage / اختر المرحلة</option><option value="Primary">Primary / ابتدائي</option><option value="Preparatory">Preparatory / إعدادي</option><option value="Secondary">Secondary / ثانوي</option>';
  const grade=document.createElement("select");grade.required=true;grade.disabled=true;grade.innerHTML='<option value="">Select stage first / اختر المرحلة أولًا</option>';
  stage.addEventListener("change",()=>{
    grade.replaceChildren(new Option("Select grade / اختر الصف",""));
    const count=({Primary:6,Preparatory:3,Secondary:3})[stage.value]||0;
    grade.disabled=!count;
    for(let i=1;i<=count;i++)grade.add(new Option(stage.value+" "+i,stage.value+" "+i));
  });
  const stageLabel=document.createElement("label");stageLabel.textContent="Stage / المرحلة";stageLabel.append(stage);
  const gradeLabel=document.createElement("label");gradeLabel.textContent="Grade / الصف";gradeLabel.append(grade);
  const button=document.createElement("button");button.type="submit";button.className="primary";button.textContent="Import questions";
  const status=document.createElement("p");status.setAttribute("role","status");
  form.append(stageLabel,gradeLabel,input,button);
  form.addEventListener("submit",async event=>{
    event.preventDefault();
    if(!input.files[0])return;
    button.disabled=true;
    const data=new FormData();data.append("file",input.files[0]);data.append("stage",stage.value);data.append("grade",grade.value);
    status.textContent="Importing...";
    try{
      const response=await fetch("/api/admin/question-bank/import",{method:"POST",body:data,credentials:"same-origin"});
      const result=await response.json().catch(()=>({}));
      if(response.status===401||response.status===403){
        throw new Error("Administrator access required / يلزم تسجيل الدخول كمدير. اضغط Admin أعلى الصفحة وأدخل كلمة مرور المدير، ثم أعد الاستيراد.");
      }
      if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"Import rejected (HTTP "+response.status+")");
      status.textContent="Imported "+result.imported+" questions into "+result.grade+" successfully / تم استيراد الأسئلة بنجاح.";
      document.getElementById("std-builder-refresh")?.click();
      if(typeof refreshAdminQuestions==="function")await refreshAdminQuestions();
    }catch(error){status.textContent="Import failed: "+error.message;}
    finally{button.disabled=false;}
  });
  panel.append(title,description,form,status);
  admin.prepend(panel);
});
