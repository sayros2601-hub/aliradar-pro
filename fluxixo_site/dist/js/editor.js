(function () {
  'use strict';
  const api = window.MiraCatalog;
  const $ = id => document.getElementById(id);
  const form = $('product-form');
  const fields = Object.fromEntries(['name', 'category', 'headline-one', 'headline-two', 'description', 'details', 'theme', 'image-note', 'demo', 'affiliate-url', 'source-url', 'original-image', 'facts'].map(id => [id, $(id)]));
  const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
  let catalog, selectedId, pendingImage = '', pendingOriginal = '', dirty = false, uploading = false, imageToken = 0;
  let originalEdited = false;

  function message(text, kind = 'success') {
    const element = $('notice');
    element.textContent = text;
    element.dataset.kind = kind;
    element.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    element.hidden = false;
  }
  function guard(action) {
    try {
      if (uploading) throw new Error('Подождите, пока изображение будет готово.');
      action();
    } catch (error) {
      message(error.message || 'Не удалось выполнить действие. Введённые данные сохранены в форме.', 'error');
    }
  }
  function currentIndex() { return catalog.products.findIndex(product => product.id === selectedId); }
  function current() { return catalog.products[currentIndex()]; }
  function markDirty() {
    dirty = true;
    $('save-state').textContent = 'Есть несохранённые изменения';
    $('save-state').classList.add('is-dirty');
  }
  function markSaved(label) {
    dirty = false;
    $('save-state').textContent = label;
    $('save-state').classList.remove('is-dirty');
  }
  function readFacts() {
    return fields.facts.value.split(/\r?\n/).map(line => line.trim()).filter(Boolean).map((line, index) => {
      const separator = line.indexOf('|');
      if (separator < 1 || !line.slice(separator + 1).trim()) throw new Error('Характеристика №' + (index + 1) + ': используйте формат «название | значение».');
      return {label: line.slice(0, separator).trim(), value: line.slice(separator + 1).trim()};
    });
  }
  function commitForm() {
    if (!form.reportValidity()) throw new Error('Проверьте выделенные поля. Изменения остаются в форме.');
    const product = Object.assign({}, current(), {
      name: fields.name.value.trim(), category: fields.category.value.trim(),
      headline: [fields['headline-one'].value.trim(), fields['headline-two'].value.trim()],
      description: fields.description.value.trim(), details: fields.details.value.trim(),
      image: pendingImage, original: originalEdited ? fields['original-image'].value.trim() : pendingOriginal,
      imageNote: fields['image-note'].value.trim(), demo: fields.demo.checked,
      affiliateUrl: fields['affiliate-url'].value.trim(), sourceUrl: fields['source-url'].value.trim(),
      theme: fields.theme.value, facts: readFacts()
    });
    const next = api.clone(catalog);
    next.products[currentIndex()] = product;
    catalog = api.validate(next);
    return catalog;
  }
  function renderList() {
    const list = $('product-list');
    list.replaceChildren();
    catalog.products.forEach((product, index) => {
      const li = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'product-button';
      button.setAttribute('aria-pressed', String(product.id === selectedId));
      button.setAttribute('aria-label', 'Редактировать: ' + product.name);
      const thumb = document.createElement('span'); thumb.className = 'product-thumb';
      const img = document.createElement('img'); img.src = product.image; img.alt = ''; img.loading = 'lazy';
      thumb.append(img);
      const summary = document.createElement('span'); summary.className = 'product-summary';
      const name = document.createElement('strong'); name.textContent = product.name;
      const state = document.createElement('small'); state.textContent = product.demo ? 'Демо-предмет' : 'Партнёрский товар';
      summary.append(name, state);
      const order = document.createElement('span'); order.className = 'product-index'; order.textContent = String(index + 1).padStart(2, '0');
      button.append(thumb, summary, order); li.append(button); list.append(li);
      button.addEventListener('click', () => guard(() => {
        if (product.id === selectedId) return;
        commitForm(); selectedId = product.id; fillForm(); renderList();
      }));
    });
    $('product-count').textContent = catalog.products.length;
    $('add-product').disabled = catalog.products.length >= 1000;
    updateItemActions();
  }
  function updateItemActions() {
    $('move-up').disabled = currentIndex() === 0;
    $('move-down').disabled = currentIndex() === catalog.products.length - 1;
    $('delete-product').disabled = catalog.products.length < 2;
    $('product-number').textContent = 'ПРЕДМЕТ ' + String(currentIndex() + 1).padStart(2, '0');
  }
  function updatePreview() {
    $('product-preview').dataset.theme = fields.theme.value;
    $('preview-category').textContent = fields.category.value || 'Категория';
    $('preview-demo').hidden = !fields.demo.checked;
    $('preview-headline-one').textContent = fields['headline-one'].value || 'Первая строка';
    $('preview-headline-two').textContent = fields['headline-two'].value || 'Вторая строка';
    $('preview-name').textContent = fields.name.value || 'Название предмета';
    fields['affiliate-url'].required = !fields.demo.checked;
    $('affiliate-optional').textContent = fields.demo.checked ? 'Необязательно для демо' : 'Обязательное поле';
  }
  function setImageInfo(name) {
    $('image-info').textContent = name || (pendingImage.startsWith('data:') ? 'Изображение встроено в каталог' : pendingImage);
  }
  function fillForm() {
    const product = current();
    imageToken += 1;
    uploading = false;
    fields.name.value = product.name; fields.category.value = product.category;
    fields['headline-one'].value = product.headline[0]; fields['headline-two'].value = product.headline[1];
    fields.description.value = product.description; fields.details.value = product.details;
    fields.theme.value = product.theme; fields['image-note'].value = product.imageNote;
    fields.demo.checked = product.demo; fields['affiliate-url'].value = product.affiliateUrl;
    fields['source-url'].value = product.sourceUrl;
    pendingOriginal = product.original; originalEdited = false;
    fields['original-image'].value = product.original.startsWith('data:') ? '' : product.original;
    fields['original-image'].placeholder = product.original.startsWith('data:') ? 'Встроенное исходное фото сохранено; введите путь для замены' : 'assets/originals/my-photo.webp';
    fields.facts.value = product.facts.map(fact => fact.label + ' | ' + fact.value).join('\n');
    pendingImage = product.image;
    $('preview-image').src = pendingImage;
    $('preview-image').alt = product.name;
    $('preview-image').style.transform = 'rotate(' + Math.max(-8, Math.min(8, product.rotation)) + 'deg)';
    $('image-file').value = '';
    $('product-id').textContent = 'ID: ' + product.id;
    setImageInfo(); updatePreview(); updateItemActions();
  }
  function save() {
    commitForm();
    catalog = api.save(catalog);
    renderList();
    markSaved('Сохранено в этом браузере');
    message('Каталог сохранён в этом браузере. Для переноса или открытия двойным щелчком скачайте catalog.js и замените файл dist/js/catalog.js.');
  }
  function uniqueId() {
    const suffix = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function' ? crypto.randomUUID().slice(0, 8) : Math.random().toString(36).slice(2, 10);
    let id = 'item-' + Date.now().toString(36) + '-' + suffix;
    while (catalog.products.some(product => product.id === id)) id += 'x';
    return id;
  }
  function reorder(direction) {
    commitForm();
    const from = currentIndex(), to = from + direction;
    if (to < 0 || to >= catalog.products.length) return;
    [catalog.products[from], catalog.products[to]] = [catalog.products[to], catalog.products[from]];
    markDirty(); renderList();
  }

  form.addEventListener('input', event => {
    if (event.target === $('image-file')) return;
    if (event.target === fields['original-image']) originalEdited = true;
    markDirty(); updatePreview();
  });
  form.addEventListener('change', event => {
    if (event.target === $('image-file')) return;
    markDirty(); updatePreview();
  });
  form.addEventListener('submit', event => {event.preventDefault(); guard(save);});
  $('save-catalog').addEventListener('click', () => guard(save));
  $('show-script-source').addEventListener('click', () => guard(() => {
    commitForm();
    $('script-source').value = api.serialize(catalog);
    $('script-source-dialog').showModal();
  }));
  $('select-script-source').addEventListener('click', () => {
    const source = $('script-source');
    source.focus();
    source.select();
    source.setSelectionRange(0, source.value.length);
  });
  $('close-script-source').addEventListener('click', () => $('script-source-dialog').close());
  $('script-source-dialog').addEventListener('close', () => {
    $('script-source').value = '';
    $('show-script-source').focus();
  });
  $('export-script').addEventListener('click', () => guard(() => {
    commitForm();
    api.download('catalog.js', api.serialize(catalog), 'text/javascript;charset=utf-8');
    message('Файл catalog.js подготовлен для скачивания. Замените им dist/js/catalog.js в папке MIRA. Если в браузере уже есть сохранённые изменения, сбросьте их к каталогу из файла.');
  }));
  $('export-json').addEventListener('click', () => guard(() => {
    commitForm();
    api.download('mira-catalog-backup.json', JSON.stringify(api.validate(catalog), null, 2), 'application/json;charset=utf-8');
    message('Резервная копия JSON подготовлена. Её можно вернуть через «Импорт JSON».');
  }));
  $('add-product').addEventListener('click', () => guard(() => {
    commitForm();
    if (catalog.products.length >= 1000) throw new Error('В каталоге может быть не более 1000 товаров.');
    const id = uniqueId();
    const product = {id, name: 'Новый предмет', category: 'Новая находка', headline: ['Новый взгляд.', 'Твоя находка.'], description: '', details: '', image: current().image, original: '', imageNote: 'Временное изображение из коллекции. Замените его фотографией нового предмета.', affiliateUrl: '', sourceUrl: '', demo: true, theme: current().theme, scale: 1, rotation: 0, facts: []};
    catalog.products.push(product); selectedId = id;
    markDirty(); fillForm(); renderList(); fields.name.focus(); fields.name.select();
    message('Добавлен демонстрационный предмет. Замените временное изображение, заполните описание и добавьте ссылку, когда товар будет готов.');
  }));
  $('delete-product').addEventListener('click', () => guard(() => {
    if (catalog.products.length < 2) throw new Error('В коллекции должен остаться хотя бы один товар.');
    const index = currentIndex();
    if (!window.confirm('Удалить «' + (fields.name.value || current().name) + '» из текущей коллекции? Несохранённые изменения этого товара тоже будут удалены.')) return;
    catalog.products.splice(index, 1);
    selectedId = catalog.products[Math.min(index, catalog.products.length - 1)].id;
    markDirty(); fillForm(); renderList(); message('Предмет удалён из текущей коллекции. Сохраните изменения или скачайте catalog.js.');
  }));
  $('move-up').addEventListener('click', () => guard(() => reorder(-1)));
  $('move-down').addEventListener('click', () => guard(() => reorder(1)));
  $('reset-catalog').addEventListener('click', () => guard(() => {
    if (!window.confirm('Удалить сохранённые в этом браузере изменения и текущие правки? Будет восстановлен каталог из файла dist/js/catalog.js. Сначала скачайте JSON, если нужна резервная копия.')) return;
    catalog = api.reset(); selectedId = catalog.products[0].id;
    fillForm(); renderList(); markSaved('Каталог из файла catalog.js');
    message('Открыт каталог из файла dist/js/catalog.js. Локальные изменения этого редактора удалены.');
  }));
  $('import-trigger').addEventListener('click', () => {if (!uploading) $('import-file').click();});
  $('import-file').addEventListener('change', event => {
    const file = event.target.files[0]; event.target.value = '';
    if (!file) return;
    if (file.size > 16000000) {message('JSON слишком большой. Максимальный размер файла — 16 МБ.', 'error'); return;}
    const reader = new FileReader();
    reader.onerror = () => message('Не удалось прочитать JSON. Текущая коллекция осталась на месте.', 'error');
    reader.onload = () => {
      try {
        const imported = api.validate(JSON.parse(String(reader.result)));
        if (!window.confirm('Импортировать ' + imported.products.length + ' товаров? Это заменит текущую коллекцию и несохранённые правки в редакторе.')) return;
        catalog = imported; selectedId = catalog.products[0].id;
        fillForm(); renderList(); markDirty();
        message('Каталог импортирован и проверен. Нажмите «Сохранить» или скачайте catalog.js, чтобы перенести его в витрину.');
      } catch (error) {message('Импорт не выполнен: ' + (error.message || 'неверный формат файла') + ' Текущая коллекция осталась на месте.', 'error');}
    };
    reader.readAsText(file);
  });
  $('image-file').addEventListener('change', event => {
    const file = event.target.files[0]; event.target.value = '';
    if (!file) return;
    if (file.size > MAX_IMAGE_BYTES) {message('Изображение больше 3 МБ. Уменьшите файл и выберите его снова.', 'error'); return;}
    if (!['image/png', 'image/webp', 'image/jpeg', 'image/avif'].includes(file.type)) {message('Поддерживаются PNG, WebP, JPEG и AVIF. Выберите изображение в одном из этих форматов.', 'error'); return;}
    const token = ++imageToken;
    uploading = true;
    $('image-info').textContent = 'Подготавливаем изображение…';
    const finishError = text => {if (token !== imageToken) return; uploading = false; setImageInfo(); message(text, 'error');};
    const reader = new FileReader();
    reader.onerror = () => finishError('Изображение не удалось прочитать. Предыдущее осталось на месте.');
    reader.onload = () => {
      if (token !== imageToken) return;
      const data = String(reader.result);
      try {api.imageUrl(data);} catch (error) {finishError(error.message); return;}
      const probe = new Image();
      probe.onload = () => {
        if (token !== imageToken) return;
        uploading = false;
        pendingImage = data;
        $('preview-image').src = data;
        $('preview-image').alt = fields.name.value;
        setImageInfo(file.name + ' · ' + probe.naturalWidth + ' × ' + probe.naturalHeight + ' · ' + Math.round(file.size / 1024) + ' КБ');
        markDirty(); message('Изображение добавлено. Оно будет встроено в catalog.js и JSON, поэтому отдельный файл для переноса не нужен.');
      };
      probe.onerror = () => finishError('Браузер не смог открыть это изображение. Попробуйте PNG или WebP.');
      probe.src = data;
    };
    reader.readAsDataURL(file);
  });
  window.addEventListener('beforeunload', event => {
    if (!dirty && !uploading) return;
    event.preventDefault(); event.returnValue = '';
  });
  window.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {event.preventDefault(); guard(save);}
  });
  try {
    const loaded = api.load(); catalog = loaded.catalog; selectedId = catalog.products[0].id;
    fillForm(); renderList(); markSaved(loaded.custom ? 'Загружены локальные изменения' : 'Исходная коллекция');
    if (loaded.warning) message(loaded.warning, 'error');
  } catch (error) {
    message('Редактор не открыл каталог: ' + error.message + ' Проверьте файл dist/js/catalog.js.', 'error');
    form.inert = true;
    for (const button of document.querySelectorAll('.toolbar button, .catalog-sidebar button, .item-actions button')) button.disabled = true;
  }
})();
