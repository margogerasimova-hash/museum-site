// Software and Computer Museum: друк заголовка по літерах і мобільне меню.
(function () {
  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) {}

  // Друк заголовка першого екрана. Повний текст лежить в aria-label і в .ghost,
  // тож без JS або за «зменшити рух» заголовок просто показується одразу.
  var typed = document.querySelector('.hero-title .typed-text');
  if (typed && !reduceMotion) {
    var full = typed.textContent;
    var n = 0;
    typed.textContent = '';
    var timer = setInterval(function () {
      n += 1;
      typed.textContent = full.slice(0, n);
      if (n >= full.length) clearInterval(timer);
    }, 80);
  }

  // Мобільне меню
  var button = document.querySelector('.menu-btn');
  var nav = document.getElementById('main-nav');
  if (button && nav) {
    var setOpen = function (open) {
      nav.classList.toggle('open', open);
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    button.addEventListener('click', function () {
      setOpen(button.getAttribute('aria-expanded') !== 'true');
    });
    // Після переходу до розділу меню закривається
    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) setOpen(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && nav.classList.contains('open')) {
        setOpen(false);
        button.focus();
      }
    });
  }

  // Кнопка «Нагору»: з’являється, коли прокрутили більше ніж на екран.
  // Без JS вона лишається прихованою (атрибут hidden), бо нічого б не робила.
  var toTop = document.querySelector('.to-top');
  if (toTop) {
    var updateToTop = function () {
      toTop.hidden = window.scrollY < window.innerHeight;
    };
    window.addEventListener('scroll', updateToTop, { passive: true });
    updateToTop();

    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
      // Фокус на початок сторінки, щоб клавіатура теж «піднялася»
      var main = document.getElementById('main');
      if (main) {
        if (!main.hasAttribute('tabindex')) main.setAttribute('tabindex', '-1');
        main.focus({ preventScroll: true });
      }
    });
  }
})();
