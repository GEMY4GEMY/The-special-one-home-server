"use strict";
async function adminRequest(url,options){
 const response=await fetch(url,{credentials:"same-origin",...options});
 if(!response.ok)throw new Error("Request failed: "+response.status);
 return response.json();
}
function showAdminMessage(id,message){document.getElementById(id).textContent=message}
async function refreshAdminQuestions(){
 const list=document.getElementById("bank-list");
 list.replaceChildren();
 try{
  const questions=await adminRequest("/api/admin/question-bank");
  if(!questions.length){list.textContent="No questions yet.";return}
  for(const question of questions){
   const row=document.createElement("div");
   row.className="result-item";
   const label=document.createElement("span");
   label.textContent=[question.grade,question.unit,question.kind,question.prompt].join(" | ");
   const edit=document.createElement("button");edit.type="button";edit.className="outline";edit.textContent="Edit";
   edit.addEventListener("click",()=>{
    const fields={"q-grade":"grade","q-unit":"unit","q-lesson":"lesson","q-difficulty":"difficulty","q-kind":"kind","q-prompt":"prompt","q-answer":"answer"};
    for(const [id,key] of Object.entries(fields))document.getElementById(id).value=question[key];
    document.getElementById("q-options").value=JSON.parse(question.options||"[]").join("\\n");
    document.getElementById("question-form").dataset.editId=question.id;
    document.getElementById("question-message").textContent="Editing question #"+question.id;
    document.getElementById("question-form").scrollIntoView({behavior:"smooth"});
   });
   const del=document.createElement("button");del.type="button";del.className="outline";del.textContent="Delete";
   del.addEventListener("click",async()=>{
    if(!confirm("Delete this question?"))return;
    try{await adminRequest("/api/admin/question-bank/"+question.id,{method:"DELETE"});await refreshAdminQuestions()}
    catch{showAdminMessage("question-message","Cannot delete question used in a draft.")}
   });
   row.append(label,edit,del);list.append(row);
  }
 }catch{list.textContent="Could not load questions."}
}
function initAdminPanel(){
 const $=id=>document.getElementById(id);
 $("refresh-questions").addEventListener("click",refreshAdminQuestions);
 $("question-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const data={
   grade:$("q-grade").value.trim(),
   unit:$("q-unit").value.trim(),
   lesson:$("q-lesson").value.trim(),
   difficulty:$("q-difficulty").value,
   kind:$("q-kind").value,
   prompt:$("q-prompt").value.trim(),
   answer:$("q-answer").value.trim(),
   options:$("q-options").value.split("\n").map(s=>s.trim()).filter(Boolean)
  };
  try{
   const editId=$("question-form").dataset.editId;
   await adminRequest(editId?"/api/admin/question-bank/"+editId:"/api/admin/question-bank",{method:editId?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
   delete $("question-form").dataset.editId;
   showAdminMessage("question-message","Question saved successfully.");
   $("q-prompt").value="";$("q-answer").value="";$("q-options").value="";
   await refreshAdminQuestions();
  }catch{showAdminMessage("question-message","Unable to save question. Check all fields.")}
 });
 $("draft-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const data={title:$("draft-title").value.trim(),grade:$("draft-grade").value.trim(),count:Number($("draft-count").value)};
  try{
   const draft=await adminRequest("/api/admin/exam-drafts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
   showAdminMessage("draft-message","Draft created: "+draft.question_count+" questions. Not yet published.");
  }catch{showAdminMessage("draft-message","Cannot generate draft. Check available questions.")}
 });
 refreshAdminQuestions();
}
document.addEventListener("DOMContentLoaded",initAdminPanel);

document.addEventListener("DOMContentLoaded",()=>{
 const form=document.getElementById("pdf-inspect-form");
 form.addEventListener("submit",async event=>{
  event.preventDefault();
  const file=document.getElementById("curriculum-pdf").files[0];
  const status=document.getElementById("pdf-inspect-status");
  const result=document.getElementById("pdf-inspect-result");
  if(!file)return;
  status.textContent="Inspecting PDF...";result.replaceChildren();
  const data=new FormData();data.append("file",file);
  try{
   const report=await adminRequest("/api/admin/pdf-inspect",{method:"POST",body:data});
   status.textContent=report.page_count+" pages inspected; "+report.image_pages+" require vision/OCR.";
   window.tsoPdfPages=report.pages;
   const pageList=document.getElementById("ai-page-list");pageList.replaceChildren();
   for(const page of report.pages){
    if(page.needs_vision){
     const vision=document.createElement("button");vision.type="button";vision.className="outline";vision.textContent="Read scanned page "+page.page;
     vision.onclick=async()=>{
      const status=document.getElementById("ai-status");status.textContent="Reading scanned page locally...";
      vision.disabled=true;
      try{
       const form=new FormData();form.append("file",file);
       const response=await fetch("/api/admin/pdf-vision?page_number="+page.page,{method:"POST",credentials:"same-origin",body:form});
       if(!response.ok)throw new Error("Vision request failed");
       const result=await response.json();page.text=result.text;page.needs_vision=false;
       status.textContent="Page "+page.page+" transcribed. Review its text before generating questions.";
       vision.textContent="Generate from page "+page.page;
       vision.onclick=()=>generatePageQuestions(page);
      }catch{status.textContent="Could not read page. Check local vision model."}
      finally{vision.disabled=false}
     };
     pageList.append(vision);
    }
    if(page.text){const button=document.createElement("button");button.type="button";button.className="outline";button.textContent="Generate from page "+page.page;button.onclick=()=>generatePageQuestions(page);pageList.append(button)}
    const detail=document.createElement("details");
    const summary=document.createElement("summary");
    summary.textContent="Page "+page.page+(page.needs_vision?" — vision required":" — text available");
    const pre=document.createElement("pre");
    pre.textContent=page.text.slice(0,1500);
    detail.append(summary,pre);result.append(detail);
   }
  }catch{status.textContent="PDF inspection failed. Check file type, size and login."}
 });
});

async function generatePageQuestions(page){
 const status=document.getElementById("ai-status");
 const list=document.getElementById("ai-suggestions");
 list.replaceChildren();status.textContent="Generating suggestions locally...";
 const grade=document.getElementById("ai-grade").value.trim();
 if(!grade){status.textContent="Enter a grade first.";return}
 try{
  const response=await adminRequest("/api/admin/ai/suggest",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({grade,page_number:page.page,page_text:page.text,count:Number(document.getElementById("ai-count").value)})});
  status.textContent=response.questions.length+" suggestions. Review before saving.";
  for(const q of response.questions){
   const card=document.createElement("article");card.className="panel";
   const prompt=document.createElement("p");prompt.textContent=q.prompt;
   const evidence=document.createElement("small");evidence.textContent="Source page "+q.source_page+": "+q.evidence_quote;
   const save=document.createElement("button");save.type="button";save.className="primary";save.textContent="Accept into question bank";
   save.onclick=()=>{
    const form=document.getElementById("question-form");
    for(const [name,value] of Object.entries({grade,kind:q.kind,difficulty:q.difficulty,prompt:q.prompt,answer:q.answer,options:q.options.join("\n")})){
     const field=form.elements.namedItem(name);if(field)field.value=value;
    }
    document.getElementById("question-message").textContent="Review unit and lesson, then press Save question.";
    form.scrollIntoView({behavior:"smooth"});
   };
   card.append(prompt,evidence,save);list.append(card);
  }
 }catch{status.textContent="Local AI not ready. Check model service and configuration."}
}
