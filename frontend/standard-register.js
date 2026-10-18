"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const toggle=document.getElementById("open-register");
  const panel=document.getElementById("register-panel");
  const form=document.getElementById("register-form");
  const status=document.getElementById("register-status");
  if(!toggle||!panel||!form)return;
  toggle.addEventListener("click",()=>{
    const open=panel.classList.toggle("hidden")===false;
    toggle.setAttribute("aria-expanded",String(open));
    if(open)document.getElementById("reg-full-name").focus();
  });
  const usernameField=document.getElementById("reg-username");
  const normalizeUsername=value=>value.trim().replace(/\s+/g,"_");
  usernameField.addEventListener("blur",()=>{
    usernameField.value=normalizeUsername(usernameField.value);
  });
  form.addEventListener("submit",async event=>{
    event.preventDefault();
    const button=form.querySelector('button[type="submit"]');
    button.disabled=true;
    status.textContent="Creating your account...";
    try{
      const values=Object.fromEntries(new FormData(form).entries());
      values.username=normalizeUsername(values.username);
      usernameField.value=values.username;
      if(!/^[A-Za-z0-9_.-]{3,80}$/.test(values.username)){
        throw Error("Use English letters, numbers or _ for username / استخدم حروف إنجليزية أو أرقام أو _ بدون مسافات");
      }
      const response=await fetch("/api/standard/register",{
        method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(values)
      });
      const data=await response.json().catch(()=>({}));
      if(!response.ok){
        const detail=typeof data.detail==="string"?data.detail:
          Array.isArray(data.detail)?data.detail.map(item=>item.msg||"Invalid field").join("; "):
          response.status===500?"Server database error / مشكلة في قاعدة بيانات السيرفر":
          "Registration failed (HTTP "+response.status+") / تعذر إنشاء الحساب";
        throw Error(detail);
      }
      document.getElementById("username").value=values.username;
      document.getElementById("password").value=values.password;
      form.reset();
      panel.classList.add("hidden");
      toggle.setAttribute("aria-expanded","false");
      document.getElementById("login-error").textContent="";
      status.textContent="";
      document.getElementById("login-form").requestSubmit();
    }catch(error){status.textContent=error instanceof TypeError?"Cannot reach server / تعذر الاتصال بالسيرفر":error.message}
    finally{button.disabled=false}
  });
});
