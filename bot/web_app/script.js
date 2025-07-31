// Инициализация Telegram Web App
Telegram.WebApp.ready();
Telegram.WebApp.expand(); // Разворачиваем Web App на весь экран

// Оборачиваем весь основной код в обработчик DOMContentLoaded
document.addEventListener('DOMContentLoaded', async () => {

    const mainPageContainer = document.getElementById('main-page-container');
    const welcomeContainer = document.getElementById('welcome-container');
    const categoriesContainer = document.getElementById('categories-container');
    const productsContainer = document.getElementById('products-container');
    const cartContainer = document.getElementById('cart-container');
    const checkoutContainer = document.getElementById('checkout-container');
    const mainCategoryTitle = document.getElementById('main-category-title');

    const courierInfoText = document.getElementById('courier-text');
    const pickupInfoText = document.getElementById('pickup-text');
    const courierDeliveryFields = document.getElementById('courier-delivery-fields');
    const pickupAddresses = document.getElementById('pickup-addresses');

    const cartItemsList = document.getElementById('cart-items-list');
    const cartTotalElement = document.getElementById('cart-total');
    const productListElement = document.getElementById('product-list');
    const checkoutForm = document.getElementById('checkout-form');
    const deliveryMethodRadios = document.querySelectorAll('input[name="deliveryMethod"]');
    const checkoutTotalElement = document.getElementById('cart-total');
    const checkoutItemsList = document.getElementById('checkout-items-list');

    const backFromCheckoutToCartButton = document.getElementById('back-from-checkout-to-cart');
    const continueShoppingButton = document.getElementById('continue-shopping-button');

    const startShoppingButton = document.getElementById('start-shopping-button');

    let cart = JSON.parse(localStorage.getItem('cart')) || {};
    let productsData = {};

    const CATEGORY_DISPLAY_MAP = {
        "category_bakery": { name: "Выпечка", emoji: "🥨" },
        "category_croissants": { name: "Круассаны", emoji: "🥐" },
        "category_artisan_bread": { name: "Ремесленный хлеб", emoji: "🍞" },
        "category_desserts": { name: "Десерты", emoji: "🍰" }
    };

    await fetchProductsData();

    function displayView(viewName, categoryKey = null) {
        welcomeContainer.classList.add('hidden');
        mainPageContainer.classList.add('hidden');
        categoriesContainer.classList.add('hidden');
        productsContainer.classList.add('hidden');
        cartContainer.classList.add('hidden');
        checkoutContainer.classList.add('hidden');
        mainCategoryTitle.classList.add('hidden');

        if (viewName === 'welcome' || viewName === 'categories') {
            Telegram.WebApp.BackButton.hide();
        } else {
            Telegram.WebApp.BackButton.show();
        }

        switch (viewName) {
            case 'welcome':
                welcomeContainer.classList.remove('hidden');
                Telegram.WebApp.MainButton.hide();
                break;
            case 'categories':
                mainPageContainer.classList.remove('hidden');
                categoriesContainer.classList.remove('hidden');
                mainCategoryTitle.textContent = 'Наше меню';
                mainCategoryTitle.classList.remove('hidden');
                loadCategories();
                Telegram.WebApp.MainButton.hide();
                break;
            case 'products':
                mainPageContainer.classList.remove('hidden');
                productsContainer.classList.remove('hidden');
                mainCategoryTitle.classList.remove('hidden');
                loadProducts(categoryKey);
                updateMainButtonCartInfo();
                break;
            case 'cart':
                mainPageContainer.classList.remove('hidden');
                cartContainer.classList.remove('hidden');
                mainCategoryTitle.textContent = 'Ваша корзина';
                mainCategoryTitle.classList.remove('hidden');
                renderCart();
                updateMainButtonCartInfo();
                break;
            case 'checkout':
                mainPageContainer.classList.remove('hidden');
                checkoutContainer.classList.remove('hidden');
                mainCategoryTitle.textContent = 'Оформление заказа';
                mainCategoryTitle.classList.remove('hidden');
                renderCheckoutSummary();
                updateMainButtonCartInfo();
                break;
            default:
                console.warn('Неизвестное представление:', viewName);
                break;
        }
    }

    Telegram.WebApp.BackButton.onClick(() => {
        const currentView = getCurrentView();
        if (currentView === 'products') {
            displayView('categories');
        } else if (currentView === 'cart') {
            const lastProductCategory = localStorage.getItem('lastProductCategory');
            if (lastProductCategory) {
                displayView('products', lastProductCategory);
                localStorage.removeItem('lastProductCategory');
            } else {
                displayView('categories');
            }
        } else if (currentView === 'checkout') {
            displayView('cart');
        } else if (currentView === 'categories') {
            if (welcomeContainer.classList.contains('hidden')) {
                 Telegram.WebApp.close();
            } else {
                displayView('welcome');
            }
        } else {
            Telegram.WebApp.close();
        }
    });

    function getCurrentView() {
        if (!welcomeContainer.classList.contains('hidden')) return 'welcome';
        if (!categoriesContainer.classList.contains('hidden')) return 'categories';
        if (!productsContainer.classList.contains('hidden')) return 'products';
        if (!cartContainer.classList.contains('hidden')) return 'cart';
        if (!checkoutContainer.classList.contains('hidden')) return 'checkout';
        return null;
    }

    function getUrlParameter(name) {
        name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
        const regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
        const results = regex.exec(location.search);
        return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
    }

    async function fetchProductsData() {
        try {
            const response = await fetch('/bot-app/api/products');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            productsData = data;
        } catch (error) {
            console.error('Ошибка при загрузке данных о продуктах:', error);
            if (Telegram.WebApp.showAlert) {
                Telegram.WebApp.showAlert('Не удалось загрузить данные о продуктах. Пожалуйста, попробуйте позже.');
            } else {
                alert('Не удалось загрузить данные о продуктах. Пожалуйста, попробуйте позже.');
            }
        }
    }

    async function loadCategories() {
        try {
            const response = await fetch('/bot-app/api/categories');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const categoriesData = await response.json();

            categoriesContainer.innerHTML = '';

            const categoriesGrid = document.createElement('div');
            categoriesGrid.className = 'categories-grid';

            categoriesData.forEach(category => {
                const categoryInfo = CATEGORY_DISPLAY_MAP[category.key] || { name: category.key, emoji: '' };
                const categoryDisplayName = categoryInfo.name;
                const categoryEmoji = categoryInfo.emoji;

                const categoryImageUrl = (productsData[category.key] && productsData[category.key].length > 0)
                    ? productsData[category.key][0].image_url
                    : 'https://placehold.co/300x200/cccccc/333333?text=No+Image';

                const categoryCard = document.createElement('div');
                categoryCard.className = 'category-card-item';
                categoryCard.dataset.categoryKey = category.key;

                categoryCard.innerHTML = `
                    <img src="${categoryImageUrl}"
                         alt="${categoryDisplayName}"
                         class="category-image"
                         onerror="this.onerror=null;this.src='https://placehold.co/300x200/cccccc/333333?text=No+Image'; this.style.backgroundColor='lightgray';">
                    <div class="category-text-wrapper">
                        <h3 class="category-title-text">${categoryEmoji} ${categoryDisplayName}</h3>
                        <div class="category-link-text">
                            <span>перейти в каталог</span>
                            <svg class="category-arrow-svg" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M10.707 2.293a1 1 0 010 1.414L6.414 8l4.293 4.293a1 1 0 01-1.414 1.414l-5-5a1 1 0 010-1.414l5-5a1 1 0 011.414 0z" transform="rotate(180 8 8)"></path>
                            </svg>
                        </div>
                    </div>
                `;

                categoryCard.addEventListener('click', () => {
                    displayView('products', category.key);
                    localStorage.setItem('lastProductCategory', category.key);
                });
                categoriesGrid.appendChild(categoryCard);
            });
            categoriesContainer.appendChild(categoriesGrid);
        } catch (error) {
            console.error('Ошибка при загрузке категорий:', error);
            if (Telegram.WebApp.showAlert) {
                Telegram.WebApp.showAlert('Не удалось загрузить категории. Пожалуйста, попробуйте позже.');
            } else {
                alert('Не удалось загрузить категории. Пожалуйста, попробуйте позже.');
            }
        }
    }

    async function loadProducts(categoryKey) {
        if (!productsData[categoryKey]) {
            await fetchProductsData();
            if (!productsData[categoryKey]) {
                if (Telegram.WebApp.showAlert) {
                    Telegram.WebApp.showAlert('Продукты для этой категории не найдены.');
                } else {
                    alert('Продукты для этой категории не найдены.');
                }
                displayView('categories');
                return;
            }
        }

        const products = productsData[categoryKey];
        mainCategoryTitle.textContent = CATEGORY_DISPLAY_MAP[categoryKey] ? CATEGORY_DISPLAY_MAP[categoryKey].name : 'Продукты';
        productListElement.innerHTML = '';

        products.forEach(product => {
            const productCard = document.createElement('div');
            productCard.className = 'product-card';
            productCard.dataset.productId = product.id;

            const quantityInCart = cart[product.id] ? cart[product.id].quantity : 0;

            productCard.innerHTML = `
                <div class="product-image-container">
                    <img src="${product.image_url || 'https://placehold.co/300x225/e0e0e0/555?text=Нет+фото'}" alt="${product.name}" class="product-image" onerror="this.onerror=null;this.src='https://placehold.co/300x225/e0e0e0/555?text=Нет+фото';">
                </div>
                <div class="product-info">
                    <div>
                        <div class="product-name">${product.name}</div>
                        <div class="product-price">${parseFloat(product.price).toFixed(2)} р.</div>
                        <div class="product-details">
                            ${product.weight && product.weight !== 'N/A' ? `<span>Вес: ${product.weight} гр.</span>` : ''}
                            ${product.availability_days && product.availability_days !== 'N/A' ? `<span>Доступен для заказа: ${product.availability_days}</span>` : ''}
                        </div>
                    </div>
                    <div>
                        <div class="quantity-controls">
                            <button data-product-id="${product.id}" data-action="decrease">-</button>
                            <span class="quantity-display" id="qty-${product.id}">${quantityInCart}</span>
                            <button data-product-id="${product.id}" data-action="increase">+</button>
                        </div>
                        <a href="${product.url}" target="_blank" class="details-link" data-product-url="${product.url}">Подробнее</a>
                    </div>
                </div>
            `;
            productListElement.appendChild(productCard);
        });

        // Добавляем обработчики событий для кнопок +/-
        productListElement.querySelectorAll('.quantity-controls button').forEach(button => {
            button.addEventListener('click', (e) => {
                const productId = e.target.dataset.productId; // Здесь может быть undefined
                const action = e.target.dataset.action;
                if (action === 'increase') {
                    updateProductQuantity(productId, 1);
                } else if (action === 'decrease') {
                    updateProductQuantity(productId, -1);
                }
            });
        });

        // Добавляем обработчики событий для кнопок "Подробнее"
        productListElement.querySelectorAll('.details-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault(); // Предотвращаем стандартное поведение ссылки
                const productUrl = e.target.dataset.productUrl;
                if (productUrl) {
                    Telegram.WebApp.openLink(productUrl); // Используем Telegram.WebApp.openLink
                } else {
                    console.warn('Предупреждение: URL продукта отсутствует для ссылки "Подробнее".');
                }
            });
        });
    }

    function updateProductQuantity(productId, change) {
        // Найти продукт во всех загруженных данных
        let product = null;
        for (const catKey in productsData) {
            product = productsData[catKey].find(p => p.id === productId);
            if (product) break;
        }

        if (!product) {
            console.error('Продукт не найден:', productId);
            return;
        }

        if (!cart[productId]) {
            cart[productId] = { ...product, quantity: 0 };
        }

        cart[productId].quantity += change;

        if (cart[productId].quantity <= 0) {
            delete cart[productId];
        }

        localStorage.setItem('cart', JSON.stringify(cart));
        updateProductCardUI(productId);
        updateMainButtonCartInfo();
    }

    function updateProductCardUI(productId) {
        const quantitySpan = document.getElementById(`qty-${productId}`); // Использование ID
        if (quantitySpan) {
            const currentQuantity = cart[productId] ? cart[productId].quantity : 0;
            quantitySpan.textContent = currentQuantity;
        }
        // Также обновим UI в корзине, если она открыта
        if (!cartContainer.classList.contains('hidden')) {
            renderCart();
        }
    }


    function renderCart() {
        cartItemsList.innerHTML = '';
        let total = 0;

        const cartItems = Object.values(cart);
        if (cartItems.length === 0) {
            cartItemsList.innerHTML = '<p class="empty-cart-message">Ваша корзина пуста.</p>';
            cartTotalElement.textContent = '0.00 р.';
            // Скрываем кнопки оформления заказа и очистки, если корзина пуста
            const cartActionsBottom = document.querySelector('.cart-actions-bottom');
            if (cartActionsBottom) cartActionsBottom.classList.add('hidden');
            // Скрываем кнопку "Продолжить покупки", если корзина пуста
            if (continueShoppingButton) continueShoppingButton.classList.add('hidden');
            return;
        } else {
            const cartActionsBottom = document.querySelector('.cart-actions-bottom');
            if (cartActionsBottom) cartActionsBottom.classList.remove('hidden');
            // Показываем кнопку "Продолжить покупки", если в корзине есть товары
            if (continueShoppingButton) continueShoppingButton.classList.remove('hidden');
        }

        cartItems.forEach(item => {
            const itemTotal = item.price * item.quantity;
            total += itemTotal;

            const cartItemElement = document.createElement('div');
            cartItemElement.className = 'cart-item';
            cartItemElement.dataset.productId = item.id;

            cartItemElement.innerHTML = `
                <img src="${item.image_url || 'https://placehold.co/80x80/cccccc/333333?text=No+Image'}" 
                     alt="${item.name}" class="cart-item-image"
                     onerror="this.onerror=null;this.src='https://placehold.co/80x80/cccccc/333333?text=No+Image';">
                <div class="cart-item-details">
                    <h4 class="cart-item-name">${item.name}</h4>
                    <p class="cart-item-price">${item.price} BYN за шт.</p>
                    <div class="cart-item-controls">
                        <button class="quantity-button decrease-cart-quantity" data-product-id="${item.id}">-</button>
                        <span class="cart-item-quantity">${item.quantity}</span>
                        <button class="quantity-button increase-cart-quantity" data-product-id="${item.id}">+</button>
                        <button class="remove-btn" data-product-id="${item.id}">Удалить</button>
                    </div>
                </div>
                <div class="cart-item-total">${itemTotal.toFixed(2)} BYN</div>
            `;
            cartItemsList.appendChild(cartItemElement);
        });

        cartTotalElement.textContent = `${total.toFixed(2)} р.`;

        // Добавляем обработчики для кнопок в корзине
        cartItemsList.querySelectorAll('.increase-cart-quantity').forEach(button => {
            button.addEventListener('click', (e) => updateProductQuantity(e.target.dataset.productId, 1));
        });
        cartItemsList.querySelectorAll('.decrease-cart-quantity').forEach(button => {
            button.addEventListener('click', (e) => updateProductQuantity(e.target.dataset.productId, -1));
        });
        cartItemsList.querySelectorAll('.remove-btn').forEach(button => { // Изменено на .remove-btn
            button.addEventListener('click', (e) => {
                const productId = e.target.dataset.productId;
                delete cart[productId];
                localStorage.setItem('cart', JSON.stringify(cart));
                renderCart(); // Перерисовываем корзину
                updateMainButtonCartInfo();
            });
        });
    }

    function clearCart() {
        cart = {};
        localStorage.removeItem('cart');
        renderCart();
        updateMainButtonCartInfo();
        if (Telegram.WebApp.showAlert) {
            Telegram.WebApp.showAlert('Корзина очищена!');
        } else {
            alert('Корзина очищена!');
        }
    }

    // Обработчики кнопок корзины (добавляем проверки на существование)
    const clearCartButton = document.getElementById('clear-cart-button');
    if (clearCartButton) {
        clearCartButton.addEventListener('click', clearCart);
    } else {
        console.error('Element with ID "clear-cart-button" not found in DOM. Cannot attach click listener.');
    }

    const checkoutButton = document.getElementById('checkout-button');
    if (checkoutButton) {
        checkoutButton.addEventListener('click', () => {
            if (Object.keys(cart).length === 0) {
                if (Telegram.WebApp.showAlert) {
                    Telegram.WebApp.showAlert('Ваша корзина пуста. Добавьте товары, чтобы оформить заказ.');
                } else {
                    alert('Ваша корзина пуста. Добавьте товары, чтобы оформить заказ.');
                }
                return;
            }
            displayView('checkout');
        });
    } else {
        console.error('Element with ID "checkout-button" not found in DOM. Cannot attach click listener.');
    }


    // --- Checkout Logic ---
    function renderCheckoutSummary() {
        checkoutItemsList.innerHTML = '';
        let total = 0;

        Object.values(cart).forEach(item => {
            const itemTotal = item.price * item.quantity;
            total += itemTotal;

            const checkoutItemElement = document.createElement('li');
            checkoutItemElement.className = 'checkout-item-summary';
            checkoutItemElement.textContent = `${item.name} x ${item.quantity} - ${itemTotal.toFixed(2)} BYN`;
            checkoutItemsList.appendChild(checkoutItemElement);
        });

        checkoutTotalElement.textContent = `${total.toFixed(2)} р.`;

        // Инициализация состояния текстовых блоков доставки и полей
        const selectedDeliveryMethod = document.querySelector('input[name="deliveryMethod"]:checked')?.value;
        toggleDeliveryFields(selectedDeliveryMethod);
    }

    // Функция для переключения видимости полей доставки/самовывоза
    function toggleDeliveryFields(method) {
        if (courierDeliveryFields && pickupAddresses) {
            if (method === 'courier') {
                courierDeliveryFields.classList.remove('hidden');
                pickupAddresses.classList.add('hidden');
                // Управляем required атрибутами
                document.getElementById('last-name').required = true;
                document.getElementById('first-name').required = true;
                document.getElementById('middle-name').required = true;
                document.getElementById('phone-number').required = true;
                document.getElementById('email').required = true;
                document.getElementById('delivery-date').required = true;
                document.getElementById('city').required = true;
                document.getElementById('address-line').required = true;
                document.querySelectorAll('input[name="pickupAddress"]').forEach(input => input.required = false);
            } else if (method === 'pickup') {
                courierDeliveryFields.classList.add('hidden');
                pickupAddresses.classList.remove('hidden');
                // Управляем required атрибутами
                document.getElementById('last-name').required = true;
                document.getElementById('first-name').required = true;
                document.getElementById('middle-name').required = true;
                document.getElementById('phone-number').required = true;
                document.getElementById('email').required = true;
                document.getElementById('delivery-date').required = true;
                document.getElementById('city').required = false;
                document.getElementById('address-line').required = false;
                document.querySelectorAll('input[name="pickupAddress"]').forEach(input => input.required = true);
            } else {
                // Если ничего не выбрано, скрываем оба и делаем все поля необязательными
                courierDeliveryFields.classList.add('hidden');
                pickupAddresses.classList.add('hidden');
                document.getElementById('last-name').required = false;
                document.getElementById('first-name').required = false;
                document.getElementById('middle-name').required = false;
                document.getElementById('phone-number').required = false;
                document.getElementById('email').required = false;
                document.getElementById('delivery-date').required = false;
                document.getElementById('city').required = false;
                document.getElementById('address-line').required = false;
                document.querySelectorAll('input[name="pickupAddress"]').forEach(input => input.required = false);
            }
        }

        // Также управляем видимостью информационных текстовых блоков
        if (courierInfoText && pickupInfoText) {
            if (method === 'courier') {
                courierInfoText.classList.remove('hidden');
                pickupInfoText.classList.add('hidden');
            } else if (method === 'pickup') {
                courierInfoText.classList.add('hidden');
                pickupInfoText.classList.remove('hidden');
            } else {
                courierInfoText.classList.add('hidden');
                pickupInfoText.classList.add('hidden');
            }
        }
    }


    // Обработчики для радио-кнопок доставки (добавляем проверки на существование)
    if (deliveryMethodRadios.length > 0) {
        deliveryMethodRadios.forEach(radio => {
            radio.addEventListener('change', (event) => {
                toggleDeliveryFields(event.target.value);
            });
        });
        // Инициализация полей при загрузке, если уже выбран метод
        const initialSelectedMethod = document.querySelector('input[name="deliveryMethod"]:checked')?.value;
        toggleDeliveryFields(initialSelectedMethod);
    } else {
        console.warn('No delivery method radio buttons found.');
    }


    // Обработчик отправки формы оформления заказа (добавляем проверку на существование)
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', (event) => {
            event.preventDefault(); // Предотвращаем стандартную отправку формы

            const formData = new FormData(checkoutForm);
            const orderDetails = {};
            for (let [key, value] of formData.entries()) {
                orderDetails[key] = value;
            }

            // Дополнительная валидация на стороне клиента
            let isValid = true;
            const errorMessages = [];

            // Валидация ФИО
            if (!orderDetails.lastName) { isValid = false; errorMessages.push('Пожалуйста, введите вашу фамилию.'); }
            if (!orderDetails.firstName) { isValid = false; errorMessages.push('Пожалуйста, введите ваше имя.'); }
            if (!orderDetails.middleName) { isValid = false; errorMessages.push('Пожалуйста, введите ваше отчество.'); }

            // Валидация телефона (простая, можно расширить regex)
            const phoneRegex = /^\+?[\d\s\-\(\)]{7,20}$/; // Пример: +375 (XX) XXX-XX-XX
            if (!orderDetails.phoneNumber || !phoneRegex.test(orderDetails.phoneNumber)) {
                isValid = false;
                errorMessages.push('Пожалуйста, введите корректный номер телефона.');
            }

            // Валидация Email
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!orderDetails.email || !emailRegex.test(orderDetails.email)) {
                isValid = false;
                errorMessages.push('Пожалуйста, введите корректный Email.');
            }

            // Валидация даты доставки
            if (!orderDetails.deliveryDate) { isValid = false; errorMessages.push('Пожалуйста, выберите дату доставки/самовывоза.'); }

            // Валидация способа доставки
            if (!orderDetails.deliveryMethod) {
                isValid = false;
                errorMessages.push('Пожалуйста, выберите способ получения.');
            } else {
                if (orderDetails.deliveryMethod === 'courier') {
                    if (!orderDetails.city) { isValid = false; errorMessages.push('Пожалуйста, выберите город для доставки.'); }
                    if (!orderDetails.addressLine) { isValid = false; errorMessages.push('Пожалуйста, введите адрес доставки.'); }
                } else if (orderDetails.deliveryMethod === 'pickup') {
                    if (!orderDetails.pickupAddress) { isValid = false; errorMessages.push('Пожалуйста, выберите адрес самовывоза.'); }
                }
            }

            if (!isValid) {
                if (Telegram.WebApp.showAlert) {
                    Telegram.WebApp.showAlert(errorMessages.join('\n'));
                } else {
                    alert('Ваш заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.');
                }
                return;
            }

            // Формируем данные для отправки в бота
            const orderPayload = {
                action: 'checkout_order',
                order_details: {
                    lastName: orderDetails.lastName,
                    firstName: orderDetails.firstName,
                    middleName: orderDetails.middleName,
                    phone: orderDetails.phoneNumber, // Используем phoneNumber из формы
                    email: orderDetails.email,
                    deliveryDate: orderDetails.deliveryDate,
                    deliveryMethod: orderDetails.deliveryMethod,
                    city: orderDetails.city || '', // Город для курьера
                    addressLine: orderDetails.addressLine || '', // Адрес для курьера
                    comment: orderDetails.commentDelivery || '', // Комментарий к доставке
                    pickupAddress: orderDetails.pickupAddress || '' // Адрес самовывоза
                },
                cart_items: Object.values(cart).map(item => ({
                    id: item.id,
                    name: item.name,
                    quantity: item.quantity,
                    price: item.price
                })),
                total_amount: parseFloat(checkoutTotalElement.textContent.replace(' р.', '')) // Парсим сумму
            };

            // Отправляем данные в Telegram бота
            Telegram.WebApp.sendData(JSON.stringify(orderPayload));

            // Очищаем корзину после отправки заказа
            clearCart();
            // Можно показать сообщение об успешном заказе и закрыть Web App
            if (Telegram.WebApp.showAlert) {
                Telegram.WebApp.showAlert('Ваш заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.');
            } else {
                alert('Ваш заказ успешно оформлен! Мы свяжемся с вами в вами в ближайшее время.');
            }
            Telegram.WebApp.close();
        });
    } else {
        console.error('Element with ID "checkout-form" not found. Cannot attach submit listener.');
    }


    // --- Telegram Web App Main Button Logic ---
    function updateMainButtonCartInfo() {
        const totalItems = Object.values(cart).reduce((sum, item) => sum + item.quantity, 0);
        const totalPrice = Object.values(cart).reduce((sum, item) => sum + (item.price * item.quantity), 0);

        if (totalItems > 0) {
            Telegram.WebApp.MainButton.setText(`🛒 Корзина (${totalItems} товаров) - ${totalPrice.toFixed(2)} р.`);
            Telegram.WebApp.MainButton.show();
        } else {
            Telegram.WebApp.MainButton.hide();
        }
    }

    // Инициализация отображения при загрузке страницы
    const initialCategory = getUrlParameter('category');
    const initialView = getUrlParameter('view');
    console.log(`DEBUG: Initializing Web App. initialView='${initialView}', initialCategory='${initialCategory}'`);


    if (initialView === 'checkout') {
        displayView('checkout');
    } else if (initialView === 'cart' || initialCategory === 'cart') {
        console.log('DEBUG: Initializing to cart view based on URL parameters.');
        displayView('cart');
    } else if (initialView === 'categories') { // ДОБАВЛЕНО: Обработка view=categories
        console.log('DEBUG: Initializing to categories view based on URL parameters.');
        displayView('categories');
    } else if (initialCategory) {
        console.log(`DEBUG: Initializing to products view for category: ${initialCategory}`);
        displayView('products', initialCategory);
    } else {
        console.log('DEBUG: Initializing to welcome view (no specific parameters).');
        displayView('welcome'); // Default to welcome view if no specific view/category is provided
    }

    if (Telegram.WebApp.MainButton) {
        Telegram.WebApp.MainButton.onClick(() => {
            displayView('cart'); // On main button click, always go to cart
        });
        updateMainButtonCartInfo(); // Update button state on load
    }

    // Обработчик для кнопки "Назад к корзине" на чекауте
    if (backFromCheckoutToCartButton) {
        backFromCheckoutToCartButton.addEventListener('click', () => displayView('cart'));
    } else {
        console.error('Element with ID "back-from-checkout-to-cart" not found in DOM. Cannot attach click listener.');
    }

    // Обработчик для кнопки "Продолжить покупки"
    if (continueShoppingButton) {
        continueShoppingButton.addEventListener('click', () => {
            const lastProductCategory = localStorage.getItem('lastProductCategory');
            if (lastProductCategory) {
                displayView('products', lastProductCategory);
            } else {
                displayView('categories'); // Если нет последней категории, идем в категории
            }
        });
    } else {
        console.error('Element with ID "continue-shopping-button" not found in DOM. Cannot attach click listener.');
    }

    // Обработчик кнопки "Заказать с доставкой" на welcome screen (с проверкой на существование)
    if (startShoppingButton) {
        startShoppingButton.addEventListener('click', () => {
            displayView('categories'); 
        });
    } else {
        console.error('Element with ID "start-shopping-button" not found in DOM. Cannot attach click listener.');
    }

}); // End of DOMContentLoaded handler
