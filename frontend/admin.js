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
   for(const page of report.pages){
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
