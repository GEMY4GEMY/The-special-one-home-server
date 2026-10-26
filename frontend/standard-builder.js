"use strict";
document.addEventListener("DOMContentLoaded",()=>{
 const admin=document.getElementById("admin-area");if(!admin)return;
 const panel=document.createElement("section");panel.className="panel admin-panel";
 panel.innerHTML='<h3>Exam Builder / إعداد الامتحان</h3><p class="muted">Choose grade, one or more units, question types and number of questions. Create and publish in one step: the assigned exam appears immediately for students in that grade.</p><form id="std-builder-form" class="admin-form"><label>Exam title<input name="title" required maxlength="150" placeholder="October Revision"></label><label>Stage / المرحلة<select id="std-builder-stage" required><option value="">Select stage / اختر المرحلة</option><option value="Primary">Primary / ابتدائي</option><option value="Preparatory">Preparatory / إعدادي</option><option value="Secondary">Secondary / ثانوي</option></select></label><label>Grade / الصف<select id="std-builder-grade" required disabled><option value="">Select stage first</option></select></label><fieldset class="wide"><legend>Units / الوحدات (select one or more)</legend><div id="std-builder-units"></div></fieldset><fieldset class="wide"><legend>Question types / أنواع الأسئلة</legend><div id="std-builder-kinds"></div></fieldset><label>Number of questions<select name="count"><option>20</option><option>40</option><option>60</option><option>80</option><option>100</option></select></label><button class="primary" type="submit">Create & show to students / إنشاء وعرض الامتحان</button></form><p id="std-builder-message" role="status"></p><button class="outline" id="std-builder-refresh" type="button">Refresh filters and published exams</button><h3>Published exams / الامتحانات المنشورة</h3><div id="std-builder-published"></div>';
 panel.insertAdjacentHTML("beforeend",'<hr><h3>Delete question bank / حذف بنك الأسئلة</h3><p class="muted">Deleting questions also removes affected exams from students. Previously recorded scores remain saved.</p><label>Delete scope / نطاق الحذف<select id="std-delete-scope"><option value="grade">Selected grade / الصف الحالي</option><option value="stage">Selected stage / المرحلة الحالية</option><option value="all">All questions / كل الأسئلة</option></select></label><button type="button" class="outline" id="std-delete-questions">Delete selected questions / حذف الأسئلة المحددة</button><p id="std-delete-status" role="status"></p>');
 admin.prepend(panel);
 const stage=panel.querySelector("#std-builder-stage"),grade=panel.querySelector("#std-builder-grade"),units=panel.querySelector("#std-builder-units"),kinds=panel.querySelector("#std-builder-kinds"),message=panel.querySelector("#std-builder-message"),published=panel.querySelector("#std-builder-published");
 const request=async(url,options={})=>{const response=await fetch(url,{credentials:"same-origin",...options});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:"Request failed");return data};
 let filters=[];
 const check=(value,group)=>{const label=document.createElement("label");label.style.display="inline-flex";label.style.alignItems="center";label.style.margin="6px";const input=document.createElement("input");input.type="checkbox";input.value=value;input.dataset.group=group;label.append(input,document.createTextNode(" "+value));return label};
 const selected=group=>[...panel.querySelectorAll('input[data-group="'+group+'"]:checked')].map(el=>el.value);
 const renderFilters=()=>{units.replaceChildren();kinds.replaceChildren();const relevant=filters.filter(x=>x.grade===grade.value);const unique=key=>[...new Set(relevant.map(x=>x[key]))];for(const u of unique("unit"))units.append(check(u,"unit"));const labels={choose:"Choose",fill:"Fill in gaps",rearrange:"Rearrange",letters:"Reorder letters"};for(const k of unique("kind")){const el=check(k,"kind");el.lastChild.textContent=" "+(labels[k]||k);kinds.append(el)}
 if(!relevant.length){units.textContent="No questions for this grade yet / لا توجد أسئلة لهذا الصف";kinds.textContent="Import questions first / استورد الأسئلة أولًا";}
 };
 function refreshGrades(preferred=""){
   grade.replaceChildren(new Option("Select grade / اختر الصف",""));
   const grades=[...new Set(filters.filter(x=>x.grade.startsWith(stage.value+" ")).map(x=>x.grade))];
   grade.disabled=!stage.value;
   for(const g of grades)grade.add(new Option(g,g));
   if(preferred&&grades.includes(preferred))grade.value=preferred;
   else if(grades.length)grade.value=grades[0];
   renderFilters();
 }
 async function refresh(){
   message.textContent="Loading available questions / جاري تحميل الأسئلة...";
   try{
     filters=await request("/api/admin/standard/filters");
     const previousGrade=grade.value;
     const stages=[...new Set(filters.map(x=>x.grade.split(" ")[0]))];
     if(!stage.value||!stages.includes(stage.value))stage.value=stages[0]||"Primary";
     refreshGrades(previousGrade);
     message.textContent=filters.length?"Loaded "+filters.reduce((sum,x)=>sum+x.total,0)+" questions / تم تحميل الأسئلة":"No questions imported yet / لم يتم استيراد أسئلة بعد";
     await refreshPublished();
   }catch(e){message.textContent="Cannot load exam filters / تعذر تحميل الاختيارات: "+e.message}
 }
 async function refreshPublished(){published.replaceChildren();for(const exam of await request("/api/admin/standard/visibility")){const row=document.createElement("div");row.className="result-item";const title=document.createElement("span");title.textContent=exam.title+" | "+exam.grade+" | "+(exam.active?"VISIBLE":"HIDDEN");const button=document.createElement("button");button.className="outline";button.textContent=exam.active?"Hide from students":"Show now";button.onclick=async()=>{button.disabled=true;try{await request("/api/admin/standard/visibility/"+encodeURIComponent(exam.id)+"/"+(exam.active?"hide":"show"),{method:"POST"});await refreshPublished()}catch(e){message.textContent=e.message;button.disabled=false}};row.append(title,button);published.append(row)}}
 panel.querySelector("#std-delete-questions").onclick=async()=>{
   const scope=panel.querySelector("#std-delete-scope").value;
   const label=scope==="all"?"ALL GRADES":scope==="stage"?stage.value:grade.value;
   if(!label){panel.querySelector("#std-delete-status").textContent="Select stage and grade first.";return}
   if(!confirm("DELETE all questions for "+label+"? Assigned exams using these questions will disappear. Student scores are preserved. / تأكيد حذف الأسئلة والامتحانات المرتبطة؟"))return;
   const typed=prompt("Type DELETE QUESTIONS to confirm / اكتب DELETE QUESTIONS للتأكيد");
   if(typed!=="DELETE QUESTIONS")return;
   const button=panel.querySelector("#std-delete-questions");button.disabled=true;
   try{const result=await request("/api/admin/standard/questions/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scope,stage:stage.value,grade:grade.value,confirm:typed})});panel.querySelector("#std-delete-status").textContent="Deleted "+result.deleted_questions+" questions and removed "+result.removed_exams+" exams. Historical scores preserved.";await refresh()}catch(err){panel.querySelector("#std-delete-status").textContent=err.message}finally{button.disabled=false}
 };
 stage.onchange=()=>refreshGrades();grade.onchange=renderFilters;panel.querySelector("#std-builder-refresh").onclick=refresh;
 panel.querySelector("#std-builder-form").onsubmit=async e=>{e.preventDefault();const form=e.currentTarget;const data={title:form.elements.title.value.trim(),grade:grade.value,units:selected("unit"),kinds:selected("kind"),count:Number(form.elements.count.value)};if(!data.units.length||!data.kinds.length){message.textContent="Choose at least one unit and question type.";return}const button=form.querySelector('button[type="submit"]');button.disabled=true;try{const draft=await request("/api/admin/standard/create-and-show",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});message.textContent="Exam is LIVE for "+draft.grade+" ("+draft.question_count+" questions) / الامتحان ظاهر الآن لطلاب الصف";await refreshPublished()}catch(err){message.textContent=err.message}finally{button.disabled=false}};
 document.addEventListener('tso:admin-login',refresh);
 if(!admin.classList.contains('hidden'))queueMicrotask(refresh);
});
