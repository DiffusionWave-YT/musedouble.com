// Each row is Spanish | English | French | Russian | Portuguese | German.
// Keep the original Spanish copy as a stable key for this buildless prototype.
const localeRows = `
Dashboard|Dashboard|Tableau de bord|Обзор|Painel|Übersicht
Get started|Get started|Premiers pas|Начало работы|Primeiros passos|Erste Schritte
Generación de imágenes|Image generation|Génération d’images|Генерация изображений|Geração de imagens|Bilder erstellen
Imagen de referencia|Reference image|Image de référence|Референс|Imagem de referência|Referenzbild
All in one|All in one|Tout-en-un|Всё в одном|Tudo em um|Alles in einem
Get prompt from photo|Photo to prompt|Photo vers prompt|Промпт по фото|Foto para prompt|Foto zu Prompt
Gallery|Gallery|Galerie|Галерея|Galeria|Galerie
Support|Support|Assistance|Поддержка|Suporte|Support
Workspace|Workspace|Espace de travail|Рабочее пространство|Área de trabalho|Arbeitsbereich
Crear|Create|Créer|Создать|Criar|Erstellen
Mi estudio|My studio|Mon studio|Моя студия|Meu estúdio|Mein Studio
Cuenta personal|Personal account|Compte personnel|Личный аккаунт|Conta pessoal|Persönliches Konto
Studio mensual|Monthly Studio|Studio mensuel|Студия на месяц|Studio mensal|Studio monatlich
Tu estudio empieza acá|Your studio starts here|Votre studio commence ici|Ваша студия начинается здесь|Seu estúdio começa aqui|Hier beginnt dein Studio
Prepará tu modelo para crear.|Prepare your model to create.|Préparez votre modèle pour créer.|Подготовьте модель для творчества.|Prepare seu modelo para criar.|Bereite dein Modell vor.
Agregar fotos|Add photos|Ajouter des photos|Добавить фото|Adicionar fotos|Fotos hinzufügen
Completar mi perfil|Complete my profile|Compléter mon profil|Заполнить профиль|Completar meu perfil|Profil vervollständigen
Ver sitio público ↗|Visit website ↗|Voir le site ↗|Открыть сайт ↗|Ver site ↗|Website ansehen ↗
Mi cuenta|My account|Mon compte|Мой аккаунт|Minha conta|Mein Konto
Vista demo|Demo preview|Aperçu démo|Демоверсия|Prévia demo|Demoansicht
¿Cómo funciona?|How does it work?|Comment ça marche ?|Как это работает?|Como funciona?|Wie funktioniert es?
Cómo funciona|How it works|Comment ça marche|Как это работает|Como funciona|So funktioniert’s
Precios|Pricing|Tarifs|Тарифы|Preços|Preise
Entrar al estudio|Enter studio|Ouvrir le studio|Войти в студию|Entrar no estúdio|Studio öffnen
Crear cuenta gratis|Create a free account|Créer un compte gratuit|Создать бесплатный аккаунт|Criar conta grátis|Kostenlos registrieren
Tu estudio personal|Your personal studio|Votre studio personnel|Ваша личная студия|Seu estúdio pessoal|Dein persönliches Studio
Tu imagen.|Your image.|Votre image.|Ваш образ.|Sua imagem.|Dein Bild.
Más posibilidades.|More possibilities.|Plus de possibilités.|Больше возможностей.|Mais possibilidades.|Mehr Möglichkeiten.
Creá contenido de vos misma. Explorá nuevos estilos, escenas y referencias desde un solo lugar.|Create content featuring you. Explore new styles, scenes and references in one place.|Créez du contenu à votre image. Explorez de nouveaux styles, scènes et références au même endroit.|Создавайте контент с собой. Открывайте новые стили, сцены и референсы в одном месте.|Crie conteúdo com sua imagem. Explore novos estilos, cenários e referências em um só lugar.|Erstelle Inhalte mit dir selbst. Entdecke neue Stile, Szenen und Vorlagen an einem Ort.
Explorá primero. Activá tu modelo cuando estés lista.|Explore first. Activate your model when you’re ready.|Explorez d’abord. Activez votre modèle quand vous êtes prête.|Сначала изучите студию. Активируйте модель, когда будете готовы.|Explore primeiro. Ative seu modelo quando estiver pronta.|Sieh dich um. Aktiviere dein Modell, wenn du bereit bist.
Luz natural / Retrato editorial|Natural light / Editorial portrait|Lumière naturelle / Portrait éditorial|Естественный свет / Редакционный портрет|Luz natural / Retrato editorial|Natürliches Licht / Editorial-Porträt
Referencia visual de stock|Stock photo reference|Photo de référence de stock|Стоковое фото для примера|Referência de banco de imagens|Stockfoto als Referenz
Simple desde el primer paso.|Simple from the first step.|Simple dès le premier pas.|Просто с первого шага.|Simples desde o primeiro passo.|Einfach vom ersten Schritt an.
Conocé tu estudio|Meet your studio|Découvrez votre studio|Знакомство со студией|Conheça seu estúdio|Lerne dein Studio kennen
Registrate gratis y explorá las herramientas y los ejemplos.|Sign up free and explore the tools and examples.|Inscrivez-vous gratuitement et explorez les outils et exemples.|Зарегистрируйтесь бесплатно и изучите инструменты и примеры.|Cadastre-se grátis e explore as ferramentas e exemplos.|Registriere dich kostenlos und entdecke Tools und Beispiele.
Prepará tu modelo|Prepare your model|Préparez votre modèle|Подготовьте модель|Prepare seu modelo|Modell vorbereiten
Subí tus fotos. Revisamos el material y tu consentimiento.|Upload your photos. We review your material and consent.|Importez vos photos. Nous vérifions le contenu et votre consentement.|Загрузите фото. Мы проверим материалы и ваше согласие.|Envie suas fotos. Revisamos o material e seu consentimento.|Lade Fotos hoch. Wir prüfen die Bilder und deine Einwilligung.
Empezá a crear|Start creating|Commencez à créer|Начните создавать|Comece a criar|Jetzt erstellen
Activá tu membresía y transformá tus ideas en nuevas imágenes.|Activate your membership and turn ideas into images.|Activez votre abonnement et transformez vos idées en images.|Активируйте подписку и воплощайте идеи в изображениях.|Ative sua assinatura e transforme ideias em imagens.|Aktiviere dein Abo und verwandle Ideen in Bilder.
Un plan. Espacio para crear.|One plan. Room to create.|Une formule. De la place pour créer.|Один тариф. Пространство для творчества.|Um plano. Espaço para criar.|Ein Tarif. Raum für Kreativität.
Para empezar|To get started|Pour commencer|Для начала|Para começar|Zum Start
Activación + primer mes|Setup + first month|Activation + premier mois|Активация + первый месяц|Ativação + primeiro mês|Einrichtung + erster Monat
Preparación de tu modelo y 200 fotos.|Model setup and 200 photos.|Préparation du modèle et 200 photos.|Подготовка модели и 200 фото.|Preparação do modelo e 200 fotos.|Modelleinrichtung und 200 Fotos.
Después, USD 100 al mes.|Then USD 100 per month.|Puis 100 USD par mois.|Затем 100 USD в месяц.|Depois, USD 100 por mês.|Danach 100 USD pro Monat.
Preparar mi perfil|Prepare my profile|Préparer mon profil|Подготовить профиль|Preparar meu perfil|Profil vorbereiten
Para seguir|Keep creating|Pour continuer|Для продолжения|Para continuar|Zum Weitermachen
/ mes|/ month|/ mois|/ месяц|/ mês|/ Monat
Tu estudio, cada mes|Your studio, every month|Votre studio, chaque mois|Ваша студия каждый месяц|Seu estúdio, todo mês|Dein Studio, jeden Monat
200 fotos mensuales.|200 photos per month.|200 photos par mois.|200 фото в месяц.|200 fotos por mês.|200 Fotos pro Monat.
Renovación automática cancelable.|Automatic renewal. Cancel anytime.|Renouvellement automatique, résiliable.|Автопродление можно отменить.|Renovação automática cancelável.|Automatische Verlängerung, jederzeit kündbar.
Cuando necesitás más|When you need more|Pour aller plus loin|Когда нужно больше|Quando precisar de mais|Wenn du mehr brauchst
100 fotos adicionales|100 extra photos|100 photos supplémentaires|100 дополнительных фото|100 fotos adicionais|100 zusätzliche Fotos
Sumá un pack a tu plan activo.|Add a pack to your active plan.|Ajoutez un pack à votre abonnement actif.|Добавьте пакет к активному тарифу.|Adicione um pacote ao seu plano ativo.|Ergänze deinen aktiven Tarif um ein Paket.
Compra puntual, sin otra suscripción.|One-time purchase. No extra subscription.|Achat ponctuel, sans autre abonnement.|Разовая покупка без новой подписки.|Compra avulsa, sem outra assinatura.|Einmaliger Kauf, kein zusätzliches Abo.
© MuseDouble · Tu imagen, tu espacio.|© MuseDouble · Your image, your space.|© MuseDouble · Votre image, votre espace.|© MuseDouble · Ваш образ, ваше пространство.|© MuseDouble · Sua imagem, seu espaço.|© MuseDouble · Dein Bild, dein Raum.
Ayuda y preguntas frecuentes ↗|Help & FAQ ↗|Aide et FAQ ↗|Помощь и вопросы ↗|Ajuda e perguntas frequentes ↗|Hilfe und FAQ ↗
Vista previa de MuseDouble · imágenes de stock · sin cobros reales|MuseDouble preview · stock photos · no real charges|Aperçu MuseDouble · photos de stock · aucun débit réel|Демо MuseDouble · стоковые фото · без реальных списаний|Prévia MuseDouble · fotos de banco · sem cobranças reais|MuseDouble-Vorschau · Stockfotos · keine echten Zahlungen
Tu estudio, en un solo lugar.|Your studio, all in one place.|Votre studio, au même endroit.|Ваша студия в одном месте.|Seu estúdio em um só lugar.|Dein Studio an einem Ort.
Configurar mi modelo|Set up my model|Configurer mon modèle|Настроить модель|Configurar meu modelo|Modell einrichten
Estado de la cuenta|Account status|État du compte|Статус аккаунта|Status da conta|Kontostatus
Cuenta gratuita|Free account|Compte gratuit|Бесплатный аккаунт|Conta gratuita|Kostenloses Konto
Tokens utilizados|Tokens used|Jetons utilisés|Использовано токенов|Tokens usados|Verwendete Tokens
Tu plan|Your plan|Votre formule|Ваш тариф|Seu plano|Dein Tarif
Después, USD 100 / mes · 200 fotos|Then USD 100 / month · 200 photos|Puis 100 USD / mois · 200 photos|Далее 100 USD / месяц · 200 фото|Depois, USD 100 / mês · 200 fotos|Danach 100 USD / Monat · 200 Fotos
1 token = 1 foto · disponibles al activar|1 token = 1 photo · available after activation|1 jeton = 1 photo · disponibles après activation|1 токен = 1 фото · после активации|1 token = 1 foto · disponíveis ao ativar|1 Token = 1 Foto · nach Aktivierung verfügbar
1 token = 1 foto · cupo de este mes|1 token = 1 photo · this month’s allowance|1 jeton = 1 photo · quota du mois|1 токен = 1 фото · лимит на месяц|1 token = 1 foto · cota do mês|1 Token = 1 Foto · Monatskontingent
Guía de bienvenida|Welcome guide|Guide de bienvenue|Вводное руководство|Guia de boas-vindas|Willkommensguide
Bienvenida a MuseDouble|Welcome to MuseDouble|Bienvenue sur MuseDouble|Добро пожаловать в MuseDouble|Bem-vinda ao MuseDouble|Willkommen bei MuseDouble
De tus fotos|From your photos|De vos photos|От ваших фото|Das suas fotos|Von deinen Fotos
a tu próxima idea.|to your next idea.|à votre prochaine idée.|к новой идее.|à sua próxima ideia.|zu deiner nächsten Idee.
Ver recorrido|Watch walkthrough|Voir le guide|Посмотреть обзор|Ver guia|Rundgang ansehen
Tu modelo, tus referencias, tu contenido.|Your model, your references, your content.|Votre modèle, vos références, votre contenu.|Ваша модель, ваши референсы, ваш контент.|Seu modelo, suas referências, seu conteúdo.|Dein Modell, deine Vorlagen, deine Inhalte.
3 pasos|3 steps|3 étapes|3 шага|3 passos|3 Schritte
Una idea. Distintas formas de crear.|One idea. Different ways to create.|Une idée. Plusieurs façons de créer.|Одна идея. Разные способы создания.|Uma ideia. Várias formas de criar.|Eine Idee. Viele Wege zum Bild.
Tus herramientas|Your tools|Vos outils|Ваши инструменты|Suas ferramentas|Deine Tools
Describí una escena y elegí tu estilo.|Describe a scene and choose your style.|Décrivez une scène et choisissez votre style.|Опишите сцену и выберите стиль.|Descreva uma cena e escolha seu estilo.|Beschreibe eine Szene und wähle deinen Stil.
Partí de una pose, una luz o un encuadre.|Start with a pose, lighting or framing.|Partez d’une pose, d’une lumière ou d’un cadrage.|Начните с позы, света или композиции.|Comece com uma pose, luz ou enquadramento.|Starte mit einer Pose, Lichtstimmung oder einem Bildausschnitt.
Tu modelo y tu referencia, juntos.|Your model and reference, together.|Votre modèle et votre référence, ensemble.|Ваша модель и референс вместе.|Seu modelo e sua referência, juntos.|Dein Modell und deine Vorlage zusammen.
Tu contenido pertenece a tu espacio privado.|Your content belongs in your private space.|Votre contenu reste dans votre espace privé.|Ваш контент — в вашем личном пространстве.|Seu conteúdo fica no seu espaço privado.|Deine Inhalte gehören in deinen privaten Bereich.
Maqueta · sin cobros ni generación real|Prototype · no real payments or generation|Maquette · sans paiement ni génération réels|Макет · без реальной оплаты и генерации|Protótipo · sem cobrança ou geração real|Prototyp · keine echten Zahlungen oder Bildgenerierung
Perfil por completar|Profile incomplete|Profil à compléter|Профиль не заполнен|Perfil incompleto|Profil unvollständig
Prepará las fotos para tu modelo.|Prepare the photos for your model.|Préparez les photos pour votre modèle.|Подготовьте фото для модели.|Prepare as fotos para seu modelo.|Bereite die Fotos für dein Modell vor.
Fotos en revisión|Photos under review|Photos en cours de vérification|Фото на проверке|Fotos em análise|Fotos werden geprüft
Tu material está pendiente de revisión.|Your material is awaiting review.|Votre contenu attend une vérification.|Ваши материалы ожидают проверки.|Seu material aguarda análise.|Deine Bilder warten auf Prüfung.
Lista para activar|Ready to activate|Prête à activer|Готово к активации|Pronta para ativar|Bereit zur Aktivierung
Tu perfil de demostración fue aprobado.|Your demo profile was approved.|Votre profil démo a été approuvé.|Ваш демопрофиль одобрен.|Seu perfil demo foi aprovado.|Dein Demoprofil wurde freigegeben.
Preparando tu modelo|Preparing your model|Préparation de votre modèle|Подготовка модели|Preparando seu modelo|Modell wird vorbereitet
La activación está completa. Estamos preparando tu estudio.|Setup is complete. We’re preparing your studio.|L’activation est terminée. Nous préparons votre studio.|Активация завершена. Мы готовим вашу студию.|Ativação concluída. Estamos preparando seu estúdio.|Die Aktivierung ist abgeschlossen. Dein Studio wird vorbereitet.
Cuenta activa|Active account|Compte actif|Аккаунт активен|Conta ativa|Konto aktiv
Tu modelo está listo para crear.|Your model is ready to create.|Votre modèle est prêt à créer.|Модель готова к созданию изображений.|Seu modelo está pronto para criar.|Dein Modell ist bereit.
Tus fotos|Your photos|Vos photos|Ваши фото|Suas fotos|Deine Fotos
Revisión|Review|Vérification|Проверка|Análise|Prüfung
Activación|Activation|Activation|Активация|Ativação|Aktivierung
Tu modelo|Your model|Votre modèle|Ваша модель|Seu modelo|Dein Modell
Activar · USD 250|Activate · USD 250|Activer · 250 USD|Активировать · 250 USD|Ativar · USD 250|Aktivieren · 250 USD
Crear imágenes|Create images|Créer des images|Создать изображения|Criar imagens|Bilder erstellen
Ver estado|View status|Voir le statut|Посмотреть статус|Ver status|Status anzeigen
Tu próximo paso|Your next step|Votre prochaine étape|Ваш следующий шаг|Seu próximo passo|Dein nächster Schritt
Todo listo para crear|Ready to create|Tout est prêt pour créer|Всё готово для творчества|Tudo pronto para criar|Bereit zum Erstellen
Completo|Complete|Terminé|Готово|Concluído|Abgeschlossen
Unos pocos pasos para preparar tu estudio.|A few simple steps to set up your studio.|Quelques étapes pour préparer votre studio.|Несколько шагов для подготовки студии.|Alguns passos para preparar seu estúdio.|Wenige Schritte bis zu deinem Studio.
Tu próximo contenido empieza con una idea.|Your next creation starts with an idea.|Votre prochaine création commence par une idée.|Ваш новый контент начинается с идеи.|Sua próxima criação começa com uma ideia.|Dein nächster Inhalt beginnt mit einer Idee.
Conocé tu estudio, gratis.|Explore your studio for free.|Découvrez votre studio gratuitement.|Изучите студию бесплатно.|Conheça seu estúdio, grátis.|Entdecke dein Studio kostenlos.
Creá tu cuenta para preparar el perfil. No necesitás una tarjeta.|Create your account to set up your profile. No card needed.|Créez un compte pour préparer votre profil. Sans carte bancaire.|Создайте аккаунт и заполните профиль. Карта не нужна.|Crie sua conta para preparar o perfil. Sem cartão.|Erstelle dein Konto und richte dein Profil ein. Keine Karte nötig.
Explorar el estudio ↗|Explore the studio ↗|Explorer le studio ↗|Изучить студию ↗|Explorar o estúdio ↗|Studio erkunden ↗
Tu espacio para crear|Your space to create|Votre espace de création|Ваше пространство для творчества|Seu espaço para criar|Dein Raum zum Erstellen
Empezá por|Start by|Commencez par|Начните со|Comece por|Starte damit,
conocer tu estudio.|exploring your studio.|découvrir votre studio.|знакомства со студией.|conhecer seu estúdio.|dein Studio zu entdecken.
Creá tu cuenta gratis. Mirá las herramientas, prepará tus fotos y activá tu modelo cuando estés lista.|Create your free account. Explore the tools, prepare your photos and activate your model when you’re ready.|Créez votre compte gratuit. Explorez les outils, préparez vos photos et activez votre modèle à votre rythme.|Создайте бесплатный аккаунт. Изучите инструменты, подготовьте фото и активируйте модель, когда будете готовы.|Crie sua conta grátis. Explore as ferramentas, prepare as fotos e ative seu modelo quando estiver pronta.|Erstelle dein kostenloses Konto. Entdecke die Tools, bereite Fotos vor und aktiviere dein Modell, wenn du bereit bist.
Sin tarjeta para registrarte.|No card required to sign up.|Inscription sans carte bancaire.|Регистрация без карты.|Cadastro sem cartão.|Registrierung ohne Karte.
Tus fotos se revisan antes del pago.|Your photos are reviewed before payment.|Vos photos sont vérifiées avant le paiement.|Фото проверяются до оплаты.|Suas fotos são analisadas antes do pagamento.|Deine Fotos werden vor der Zahlung geprüft.
USD 250 al activar; luego USD 100 al mes.|USD 250 to activate, then USD 100/month.|250 USD à l’activation, puis 100 USD/mois.|250 USD при активации, затем 100 USD/месяц.|USD 250 para ativar; depois USD 100/mês.|250 USD zur Aktivierung, danach 100 USD/Monat.
Volver al sitio|Back to website|Retour au site|Вернуться на сайт|Voltar ao site|Zurück zur Website
Registro gratuito|Free signup|Inscription gratuite|Бесплатная регистрация|Cadastro gratuito|Kostenlose Registrierung
Tu cuenta en MuseDouble|Your MuseDouble account|Votre compte MuseDouble|Ваш аккаунт MuseDouble|Sua conta MuseDouble|Dein MuseDouble-Konto
Tu nombre|Your name|Votre prénom|Ваше имя|Seu nome|Dein Name
Cómo querés que te llamemos|What should we call you?|Comment vous appeler ?|Как к вам обращаться?|Como podemos chamar você?|Wie sollen wir dich nennen?
Email|Email|E-mail|Электронная почта|Email|E-Mail
vos@ejemplo.com|you@example.com|vous@exemple.com|you@example.com|voce@exemplo.com|du@beispiel.de
Registro de demostración. No se crea una cuenta real ni se envía un email. Tus datos se borran al recargar.|Demo signup. No real account or email is created. Your details clear when you reload.|Inscription de démonstration. Aucun compte réel ni e-mail envoyé. Vos données s’effacent au rechargement.|Деморегистрация. Реальный аккаунт не создаётся, письма не отправляются. Данные сбросятся при перезагрузке.|Cadastro demo. Nenhuma conta real ou email é criado. Os dados são apagados ao recarregar.|Demo-Registrierung. Kein echtes Konto, kein E-Mail-Versand. Beim Neuladen werden deine Daten gelöscht.
Crear cuenta de demostración|Create demo account|Créer un compte démo|Создать демоаккаунт|Criar conta demo|Demokonto erstellen
o explorá sin completar datos|or explore without entering details|ou explorez sans saisir de données|или изучите без ввода данных|ou explore sem preencher dados|oder ohne Angaben erkunden
Usar cuenta de ejemplo|Use sample account|Utiliser un compte exemple|Использовать пример аккаунта|Usar conta de exemplo|Beispielkonto verwenden
Ingresá tu nombre.|Enter your name.|Saisissez votre prénom.|Введите имя.|Digite seu nome.|Gib deinen Namen ein.
Cuenta de demostración creada.|Demo account created.|Compte démo créé.|Демоаккаунт создан.|Conta demo criada.|Demokonto erstellt.
Ya estás explorando con una cuenta de ejemplo.|You’re exploring with a sample account.|Vous explorez avec un compte exemple.|Вы используете пример аккаунта.|Você está usando uma conta de exemplo.|Du nutzt jetzt ein Beispielkonto.
Empecemos por vos.|Let’s start with you.|Commençons par vous.|Начнём с вас.|Vamos começar com você.|Beginnen wir mit dir.
Estas fotos nos ayudan a preparar tu modelo personal.|These photos help us prepare your personal model.|Ces photos nous aident à préparer votre modèle personnel.|Эти фото помогут подготовить вашу персональную модель.|Estas fotos ajudam a preparar seu modelo pessoal.|Diese Fotos helfen uns, dein persönliches Modell vorzubereiten.
01 / Tu material|01 / Your photos|01 / Vos photos|01 / Ваши фото|01 / Suas fotos|01 / Deine Fotos
Fotos claras. Sin filtros.|Clear photos. No filters.|Des photos nettes. Sans filtres.|Чёткие фото. Без фильтров.|Fotos nítidas. Sem filtros.|Klare Fotos. Ohne Filter.
Incluí rostro de frente y perfil, planos de medio cuerpo y cuerpo completo. Variá los ángulos y mantené una buena iluminación.|Include front and profile portraits, half-body and full-body shots. Vary the angles and use good lighting.|Ajoutez des portraits de face et de profil, à mi-corps et en pied. Variez les angles avec un bon éclairage.|Добавьте фото лица анфас и в профиль, по пояс и в полный рост. Меняйте ракурсы и используйте хорошее освещение.|Inclua rosto de frente e perfil, meio corpo e corpo inteiro. Varie os ângulos com boa iluminação.|Nutze Porträts von vorn und im Profil sowie Halb- und Ganzkörperbilder. Variiere die Winkel bei guter Beleuchtung.
Subí tus fotos de entrenamiento|Upload your training photos|Importez vos photos d’entraînement|Загрузите фото для обучения|Envie suas fotos de treinamento|Trainingsfotos hochladen
Elegí una imagen de referencia|Choose a reference image|Choisissez une image de référence|Выберите референс|Escolha uma imagem de referência|Referenzbild auswählen
Arrastrá las imágenes o seleccioná desde tu dispositivo.|Drag images here or choose from your device.|Glissez vos images ici ou sélectionnez-les sur votre appareil.|Перетащите изображения или выберите на устройстве.|Arraste imagens ou selecione no dispositivo.|Bilder hierher ziehen oder auf deinem Gerät auswählen.
JPG, PNG o WebP · hasta 20 MB por foto|JPG, PNG or WebP · up to 20 MB per photo|JPG, PNG ou WebP · 20 Mo maximum par photo|JPG, PNG или WebP · до 20 МБ на фото|JPG, PNG ou WebP · até 20 MB por foto|JPG, PNG oder WebP · bis zu 20 MB pro Foto
Confirmo que soy mayor de 18 años, que las fotos son mías y que tengo derecho a utilizarlas.|I confirm I’m over 18, these photos are of me and I have the right to use them.|Je confirme avoir plus de 18 ans, figurer sur ces photos et avoir le droit de les utiliser.|Подтверждаю, что мне больше 18 лет, на фото изображён я и у меня есть право их использовать.|Confirmo ter mais de 18 anos, que as fotos são minhas e que tenho direito de usá-las.|Ich bestätige, dass ich über 18 bin, selbst auf den Fotos zu sehen bin und sie verwenden darf.
En esta demo las fotos se muestran solo en tu navegador. No se envían, guardan ni usan para entrenar un modelo.|In this demo, photos stay in your browser. They aren’t sent, saved or used to train a model.|Dans cette démo, les photos restent dans votre navigateur. Elles ne sont ni envoyées, ni enregistrées, ni utilisées pour entraîner un modèle.|В демоверсии фото остаются в браузере. Они не отправляются, не сохраняются и не используются для обучения.|Nesta demo, as fotos ficam no navegador. Não são enviadas, salvas nem usadas para treinar um modelo.|In dieser Demo bleiben Fotos im Browser. Sie werden weder gesendet noch gespeichert oder zum Training verwendet.
Continuar a revisión|Continue to review|Passer à la vérification|Перейти к проверке|Continuar para análise|Weiter zur Prüfung
Guía de fotos|Photo guide|Guide photo|Руководство по фото|Guia de fotos|Fotoanleitung
Que se te vea bien.|Show yourself clearly.|Montrez-vous clairement.|Пусть вас будет хорошо видно.|Mostre-se com clareza.|Zeige dich deutlich.
Rostro visible|Visible face|Visage visible|Лицо видно|Rosto visível|Gesicht sichtbar
Distintos encuadres|Different framing|Cadrages variés|Разные ракурсы|Enquadramentos variados|Verschiedene Bildausschnitte
Luz uniforme y buena resolución.|Even lighting and good resolution.|Lumière uniforme et bonne résolution.|Ровный свет и хорошее разрешение.|Luz uniforme e boa resolução.|Gleichmäßiges Licht und gute Auflösung.
Una sola persona en cada imagen.|Only you in each photo.|Une seule personne par image.|Один человек на каждом фото.|Uma pessoa em cada imagem.|Nur eine Person pro Bild.
Rostro sin lentes de sol ni filtros.|No sunglasses or face filters.|Sans lunettes de soleil ni filtres.|Без солнцезащитных очков и фильтров.|Sem óculos escuros ou filtros.|Keine Sonnenbrille oder Gesichtsfilter.
Incluí frente, perfil y cuerpo completo.|Include front, profile and full-body views.|Incluez face, profil et vue en pied.|Добавьте анфас, профиль и полный рост.|Inclua frente, perfil e corpo inteiro.|Von vorn, im Profil und in voller Körpergröße.
Fotografías de stock orientativas. La cantidad final de imágenes se definirá con el equipo de producción.|Stock photos for guidance. The production team will confirm the final number of images.|Photos de stock à titre indicatif. L’équipe de production confirmera le nombre final d’images.|Стоковые фото для примера. Команда уточнит итоговое количество снимков.|Fotos de banco como orientação. A equipe definirá a quantidade final.|Stockfotos zur Orientierung. Das Produktionsteam legt die endgültige Anzahl fest.
Primero revisamos tu material. Después activás el plan: USD 250 con el primer mes y 200 fotos incluidos.|We review your photos first. Then activate for USD 250, including the first month and 200 photos.|Nous vérifions d’abord vos photos. Activez ensuite pour 250 USD, avec le premier mois et 200 photos.|Сначала проверяем фото. Затем активация за 250 USD с первым месяцем и 200 фото.|Primeiro analisamos suas fotos. Depois, ative por USD 250, com primeiro mês e 200 fotos.|Wir prüfen zuerst deine Fotos. Danach aktivierst du für 250 USD inklusive erstem Monat und 200 Fotos.
Usar fotos de ejemplo para probar|Try with sample photos|Essayer avec des photos exemples|Попробовать с примерами фото|Testar com fotos de exemplo|Mit Beispielfotos testen
Estoy probando el recorrido con fotografías de stock. Esta simulación no verifica identidad ni constituye un consentimiento real.|I’m testing the flow with stock photos. This simulation does not verify identity or constitute real consent.|Je teste le parcours avec des photos de stock. Cette simulation ne vérifie pas l’identité et ne constitue pas un consentement réel.|Я пробую процесс со стоковыми фото. Это не проверка личности и не реальное согласие.|Estou testando com fotos de banco. Esta simulação não verifica identidade nem constitui consentimento real.|Ich teste den Ablauf mit Stockfotos. Die Simulation prüft keine Identität und stellt keine echte Einwilligung dar.
Los ejemplos ya están cargados.|Sample photos are already loaded.|Les exemples sont déjà chargés.|Примеры уже загружены.|Os exemplos já foram carregados.|Beispiele sind bereits geladen.
Fotos de ejemplo listas.|Sample photos ready.|Photos exemples prêtes.|Примеры фото готовы.|Fotos de exemplo prontas.|Beispielfotos bereit.
Seleccioná fotos o usá los ejemplos.|Select photos or use the examples.|Choisissez des photos ou utilisez les exemples.|Выберите фото или используйте примеры.|Selecione fotos ou use os exemplos.|Wähle Fotos oder verwende die Beispiele.
Marcá la declaración para continuar.|Check the declaration to continue.|Cochez la déclaration pour continuer.|Отметьте подтверждение для продолжения.|Marque a declaração para continuar.|Bestätige die Erklärung, um fortzufahren.
Elegí imágenes JPG, PNG o WebP de hasta 20 MB.|Choose JPG, PNG or WebP images up to 20 MB.|Choisissez des images JPG, PNG ou WebP de 20 Mo maximum.|Выберите JPG, PNG или WebP до 20 МБ.|Escolha JPG, PNG ou WebP de até 20 MB.|Wähle JPG, PNG oder WebP bis 20 MB.
`;
