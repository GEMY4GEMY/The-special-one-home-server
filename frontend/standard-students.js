"use strict";
document.addEventListener("DOMContentLoaded",()=>{
 const admin=document.getElementById("admin-area");if(!admin)return;
 const panel=document.createElement("section");panel.className="panel admin-panel";
 panel.innerHTML='<h3>Student accounts / حسابات الطلاب</h3><p class="muted">Admin only — create student logins and view enrolled students.</p><form id="std-student-form" class="admin-form"><label>Student full name<input name="full_name" required maxlength="120" autocomplete="off"></label><label>Username<input name="username" required maxlength="80" autocomplete="off"></label><label>Student code<input name="student_code" required maxlength="80"></label><label>Grade<input name="grade" required maxlength="80" placeholder="Primary 3"></label><label>Password<input name="password" type="password" required minlength="10" autocomplete="new-password"></label><button class="primary" type="submit">Create student user +</button></form><p id="std-student-status" role="status"></p><button id="std-student-refresh" type="button" class="outline">View students</button><div id="std-student-list" class="results"></div>';
 admin.prepend(panel);
 const form=panel.querySelector("#std-student-form"),status=panel.querySelector("#std-student-status"),list=panel.querySelector("#std-student-list");
 const request=async(url,options={})=>{const response=await fetch(url,{credentials:"same-origin",...options});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:"Request failed");return data};
 const refresh=async()=>{list.replaceChildren();try{const students=await request("/api/students");if(!students.length){list.textContent="No student accounts yet.";return}for(const s of students){const row=document.createElement("p");row.className="result-item";row.textContent=s.full_name+" | "+s.student_code+" | "+s.grade;list.append(row)}}catch(e){list.textContent=e.message}};
 form.onsubmit=async event=>{event.preventDefault();const button=form.querySelector("button[type=submit]");button.disabled=true;status.textContent="Creating student...";
 try{const data=Object.fromEntries(new FormData(form).entries());await request("/api/students",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});status.textContent="Student account created successfully.";form.reset();await refresh()}catch(e){status.textContent="Cannot create student: "+e.message}finally{button.disabled=false}};
 panel.querySelector("#std-student-refresh").onclick=refresh;
});
