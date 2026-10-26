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
  const button=document.createElement("button");button.type="submit";button.className="primary";button.textContent="Import questions";
  const status=document.createElement("p");status.setAttribute("role","status");
  form.append(input,button);
  form.addEventListener("submit",async event=>{
    event.preventDefault();
    if(!input.files[0])return;
    button.disabled=true;
    const data=new FormData();data.append("file",input.files[0]);
    status.textContent="Importing...";
    try{
      const response=await fetch("/api/admin/question-bank/import",{method:"POST",body:data,credentials:"same-origin"});
      const result=await response.json().catch(()=>({}));
      if(response.status===401||response.status===403){
        throw new Error("Administrator access required / يلزم تسجيل الدخول كمدير. اضغط Admin أعلى الصفحة وأدخل كلمة مرور المدير، ثم أعد الاستيراد.");
      }
      if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"Import rejected (HTTP "+response.status+")");
      status.textContent="Imported "+result.imported+" questions successfully.";
      if(typeof refreshAdminQuestions==="function")await refreshAdminQuestions();
    }catch(error){status.textContent="Import failed: "+error.message;}
    finally{button.disabled=false;}
  });
  panel.append(title,description,form,status);
  admin.prepend(panel);
});
