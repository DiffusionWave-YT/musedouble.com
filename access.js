// Presentation flow only. Replace with server sessions and OAuth before launch.
const accessRows = `
Registrate para entrar al estudio|Sign up to enter the studio|Inscrivez-vous pour accéder au studio|Зарегистрируйтесь для входа в студию|Cadastre-se para entrar no estúdio|Registriere dich für das Studio
Iniciar sesión|Log in|Se connecter|Войти|Entrar|Anmelden
Continuar con Google|Continue with Google|Continuer avec Google|Продолжить с Google|Continuar com Google|Mit Google fortfahren
Crear mi cuenta gratuita|Create my free account|Créer mon compte gratuit|Создать бесплатный аккаунт|Criar minha conta gratuita|Kostenloses Konto erstellen
Ya tengo una cuenta|I already have an account|J’ai déjà un compte|У меня уже есть аккаунт|Já tenho uma conta|Ich habe bereits ein Konto
Volvé a tu estudio.|Welcome back to your studio.|Retrouvez votre studio.|Вернитесь в свою студию.|Volte ao seu estúdio.|Willkommen zurück in deinem Studio.
Entrá con tu email o tu cuenta de Google.|Log in with your email or Google account.|Connectez-vous avec votre email ou Google.|Войдите через email или Google.|Entre com seu email ou Google.|Melde dich mit E-Mail oder Google an.
Continuar con email|Continue with email|Continuer avec l’email|Продолжить с email|Continuar com email|Mit E-Mail fortfahren
o con tu email|or with your email|ou avec votre email|или через email|ou com seu email|oder mit deiner E-Mail
Afiliados|Affiliates|Affiliés|Партнёры|Afiliados|Partner
Cerrar sesión|Log out|Se déconnecter|Выйти|Sair|Abmelden
Este acceso no está disponible por el momento. Intentá más tarde.|This sign-in option is currently unavailable. Please try again later.|Cette connexion est indisponible. Réessayez plus tard.|Этот способ входа пока недоступен. Попробуйте позже.|Este acesso está indisponível. Tente mais tarde.|Diese Anmeldung ist derzeit nicht verfügbar. Bitte später erneut versuchen.
Tus límites, tu decisión.|Your boundaries. Your choice.|Vos limites, votre choix.|Ваши границы — ваш выбор.|Seus limites, sua decisão.|Deine Grenzen, deine Entscheidung.
Podés preparar tu modelo con ropa. Las referencias íntimas son opcionales y solo deben incluir lo que vos elijas compartir.|You can prepare your model fully clothed. Intimate references are optional and should include only what you choose to share.|Vous pouvez préparer votre modèle habillée. Les références intimes sont facultatives et limitées à ce que vous choisissez de partager.|Модель можно подготовить по фото в одежде. Интимные фото необязательны: делитесь только тем, что выбрали сами.|Você pode preparar seu modelo com roupa. Referências íntimas são opcionais e devem incluir só o que você escolher compartilhar.|Du kannst dein Modell bekleidet vorbereiten. Intime Referenzen sind freiwillig: Teile nur, was du selbst möchtest.
Imágenes utilizadas|Images used|Images utilisées|Использовано изображений|Imagens utilizadas|Verwendete Bilder
Imágenes disponibles|Images available|Images disponibles|Доступно изображений|Imagens disponíveis|Verfügbare Bilder
Ejemplos censurados.|Censored examples.|Exemples censurés.|Примеры с цензурой.|Exemplos censurados.|Zensierte Beispiele.
Tu primer mes comienza cuando tu modelo esté listo.|Your first month starts when your model is ready.|Votre premier mois commence lorsque votre modèle est prêt.|Первый месяц начинается, когда модель готова.|Seu primeiro mês começa quando seu modelo estiver pronto.|Dein erster Monat beginnt, sobald dein Modell bereit ist.
Tu imagen, un estudio de posibilidades.|Your image, a studio of possibilities.|Votre image, un studio de possibilités.|Ваш образ — новые возможности.|Sua imagem, um estúdio de possibilidades.|Dein Bild, ein Studio voller Möglichkeiten.
Tu material se revisa antes de activar el modelo.|Your material is reviewed before model activation.|Vos photos sont vérifiées avant l’activation.|Ваши материалы проверяются до активации модели.|Seu material é analisado antes de ativar o modelo.|Deine Bilder werden vor der Modellaktivierung geprüft.
Completá la verificación de identidad y la firma del contrato antes de activar.|Complete identity verification and sign the agreement before activation.|Vérifiez votre identité et signez le contrat avant l’activation.|Подтвердите личность и подпишите договор до активации.|Verifique sua identidade e assine o contrato antes da ativação.|Bestätige deine Identität und unterzeichne den Vertrag vor der Aktivierung.
`;
for (const row of accessRows.trim().split('\n')) {
 const values=row.split('|'); translations.set(values[0],Object.fromEntries(languageOrder.map((code,i)=>[code,values[i]])));
}
// Retain stable translation keys while removing internal prototype annotations.
const quietCopy=/simulad|simulat|demo|démo|demonstr|demostr|демо|maqueta|mockup|prototype|prototyp|protótipo|maquette|sin cobros|no real|no se realizará|no se envi|no son cobros|se incorporarán|solo en este navegador|only in this browser/i;
for(const [key,values] of translations){
 if(quietCopy.test(key)) for(const code of languageOrder) values[code]='';
}
function aliasCopy(key,replacement){translations.set(key,translations.get(replacement));}
aliasCopy('Tokens utilizados','Imágenes utilizadas');aliasCopy('Tokens disponibles','Imágenes disponibles');
aliasCopy('Entrar al estudio','Registrate para entrar al estudio');
aliasCopy('Ejemplos censurados para esta vista previa.','Ejemplos censurados.');
aliasCopy('En esta demo las fotos se muestran solo en tu navegador. No se envían, guardan ni usan para entrenar un modelo.','Tu material se revisa antes de activar el modelo.');
aliasCopy('La verificación y la firma reales se incorporarán antes de habilitar cobros.','Completá la verificación de identidad y la firma del contrato antes de activar.');

function accessView(login=false){return `<div class="signup-page"><header><a href="#home">${brand()}</a><a href="#${login?'signup':'login'}">${login?'Crear mi cuenta gratuita':'Ya tengo una cuenta'}</a></header><main class="signup-grid"><section class="signup-copy"><span class="eyebrow">MuseDouble</span><h1>${login?'Volvé a tu estudio.':'Registrate para entrar al estudio'}</h1><p>${login?'Entrá con tu email o tu cuenta de Google.':'Creá tu cuenta gratis. Mirá las herramientas, prepará tus fotos y activá tu modelo cuando estés lista.'}</p><ul class="checklist"><li>${icon('check')} Sin tarjeta para registrarte.</li><li>${icon('check')} Tus fotos se revisan antes del pago.</li><li>${icon('check')} USD 250 al activar; luego USD 100 al mes.</li></ul><a class="text-btn" href="#home">Volver al sitio</a></section><section class="card signup-card"><span class="badge purple">${login?'Iniciar sesión':'Registro gratuito'}</span><h2>Tu cuenta en MuseDouble</h2><button class="btn full" onclick="googleSignIn()"><span aria-hidden="true">G</span> Continuar con Google</button><div class="signup-divider">o con tu email</div><form onsubmit="${login?'loginMember':'registerMember'}(event)">${login?'':'<label class="field" for="creator-name">Tu nombre</label><input id="creator-name" name="name" autocomplete="given-name" required maxlength="60" placeholder="Cómo querés que te llamemos">'}<label class="field" for="creator-email">Email</label><input id="creator-email" name="email" type="email" autocomplete="email" required maxlength="254" placeholder="vos@ejemplo.com"><button class="btn primary full" style="margin-top:24px" type="submit">${login?'Continuar con email':'Crear mi cuenta gratuita'} ${icon('arrow')}</button></form></section></main></div>`;}
registerView=()=>accessView(false);views.signup=registerView;views.login=()=>accessView(true);
registerMember=function(event){event.preventDefault();const form=event.target;if(!form.reportValidity())return;member.name=form.elements.name.value.trim();if(!member.name)return;member.email=form.elements.email.value.trim();member.registered=true;location.hash='dashboard';};
// Hook endpoints must be connected by the engineer. Never simulate a Google identity.
function googleSignIn(){if(window.MUSEDOUBLE_AUTH?.googleUrl)location.assign(window.MUSEDOUBLE_AUTH.googleUrl);else toast('Este acceso no está disponible por el momento. Intentá más tarde.');}
function loginMember(event){event.preventDefault();if(!event.target.reportValidity())return;if(member.registered&&member.email===event.target.elements.email.value.trim()){location.hash='dashboard';return;}toast('Este acceso no está disponible por el momento. Intentá más tarde.');}
function logoutMember(){member.registered=false;member.name='';member.email='';active=false;used=0;extra=0;results=[];for(const item of uploads)URL.revokeObjectURL(item.url);uploads=[];if(reference)URL.revokeObjectURL(reference.url);reference=null;Object.assign(member,{stage:'draft',identity:false,contract:false,consent:false,payments:[],periodEnd:null,renew:true});modal.close();location.hash='home';}
const publicFooter=()=>`<footer><span>© MuseDouble · Tu imagen, tu espacio.</span><div class="footer-links"><a href="https://partners.musedouble.com" target="_blank" rel="noopener"><span>Afiliados</span> ↗</a><a href="#support">Support</a><a href="#login">Iniciar sesión</a></div></footer>`;
const accessHome=home;
home=function(){return accessHome().replace(/<div class="demo-bar">[\s\S]*?<\/div>/g,'').replace('href="#dashboard">Entrar al estudio','href="#signup">Registrate para entrar al estudio').replace(/<footer>[\s\S]*?<\/footer>/,publicFooter()).replace('<div class="public-links">','<div class="public-links"><a href="#login">Iniciar sesión</a>');};
function cleanPresentation(){
 document.querySelectorAll('.demo-controls,.demo-bar,.register-banner').forEach(el=>el.remove());
 // Remove internal implementation notes, including before the translator runs.
 document.querySelectorAll('.notice,.footnote>span,.small,.badge,.faq details,.guide-language-note').forEach(el=>{if(quietCopy.test(el.textContent)&&!el.querySelector('input,button,select')&&!translations.get(el.textContent.trim())?.en)el.remove();});
 document.querySelectorAll('[onclick="samplePhotos()"],.signup-divider+.btn[onclick="registerSample()"] ').forEach(el=>el.remove());
 const actions=document.querySelector('.top-actions');if(actions&&!actions.querySelector('[data-logout]'))actions.insertAdjacentHTML('beforeend','<button data-logout class="text-btn" onclick="logoutMember()">Cerrar sesión</button>');
 const boundary=document.querySelector('.boundary-card');if(boundary&&!boundary.querySelector('[data-boundaries]'))boundary.insertAdjacentHTML('afterbegin','<div data-boundaries><h2>Tus límites, tu decisión.</h2><p>Podés preparar tu modelo con ropa. Las referencias íntimas son opcionales y solo deben incluir lo que vos elijas compartir.</p></div>');
 const pricing=document.querySelector('#pricing');if(pricing&&!pricing.querySelector('[data-start-month]'))pricing.insertAdjacentHTML('beforeend','<p data-start-month class="small muted">Tu primer mes comienza cuando tu modelo esté listo.</p>');
}
const beforeAccessLocalize=localizePage;
localizePage=function(){cleanPresentation();beforeAccessLocalize();document.querySelector('meta[name="description"]').content=translateCopy('Tu imagen, un estudio de posibilidades.');};
const beforeAccessRender=render;
window.removeEventListener('hashchange',render);
render=function(){let page=route();if(!['home','signup','login','support'].includes(page)&&!member.registered){history.replaceState(null,'','#signup');page='signup';}if(page==='login'){app.innerHTML=accessView(true);window.scrollTo(0,0);}else if(page==='support'&&!member.registered){app.innerHTML='<div class="public"><nav><a href="#home">'+brand()+'</a><a href="#signup">Crear mi cuenta gratuita</a></nav><main class="main">'+support()+'</main>'+publicFooter()+'</div>';}else beforeAccessRender();localizePage();};
window.addEventListener('hashchange',render);if(!document.body.hasAttribute('data-live-backend'))render();
