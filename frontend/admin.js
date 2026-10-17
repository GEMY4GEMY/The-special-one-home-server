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
   row.textContent=[question.grade,question.unit,question.kind,question.prompt].join(" | ");
   list.append(row);
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
   await adminRequest("/api/admin/question-bank",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
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
