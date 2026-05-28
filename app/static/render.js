window.Render = (function () {
  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtQty(q) {
    var n = parseFloat(q) || 0;
    return n === Math.floor(n) ? String(Math.floor(n)) : String(n);
  }

  function daysUntil(dateStr) {
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var target = new Date(dateStr + 'T00:00:00');
    return Math.round((target - today) / 86400000);
  }

  function expiryBadge(expiresAt) {
    if (!expiresAt) {
      return '<span class="text-xs bg-gray-100 text-gray-400 px-2 py-0.5 rounded-full">No expiry</span>';
    }
    var d = daysUntil(expiresAt);
    if (d < 0) return '<span class="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">Expired</span>';
    if (d === 0) return '<span class="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">Expires today</span>';
    if (d <= 3) return '<span class="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">' + d + 'd left</span>';
    if (d <= 7) return '<span class="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">' + d + 'd left</span>';
    return '<span class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">' + d + 'd left</span>';
  }

  function dashboardExpiryBadge(expiresAt) {
    var d = daysUntil(expiresAt);
    if (d < 0) return '<span class="text-xs font-semibold bg-red-100 text-red-700 px-2.5 py-1 rounded-full">Expired</span>';
    if (d === 0) return '<span class="text-xs font-semibold bg-red-100 text-red-700 px-2.5 py-1 rounded-full">Today</span>';
    if (d <= 3) return '<span class="text-xs font-semibold bg-red-100 text-red-700 px-2.5 py-1 rounded-full">' + d + 'd left</span>';
    return '<span class="text-xs font-semibold bg-yellow-100 text-yellow-700 px-2.5 py-1 rounded-full">' + d + 'd left</span>';
  }

  function fmtTime(isoStr) {
    var d = new Date(isoStr);
    var h = d.getHours();
    var m = String(d.getMinutes()).padStart(2, '0');
    var ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return h + ':' + m + ' ' + ampm;
  }

  var MEAL_COLORS = {
    BREAKFAST: 'bg-orange-100 text-orange-700',
    LUNCH: 'bg-blue-100 text-blue-700',
    DINNER: 'bg-purple-100 text-purple-700',
    SNACK: 'bg-yellow-100 text-yellow-700',
  };

  function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }

  function itemList(query) {
    var el = document.getElementById('item-list');
    if (!el) return;
    var items = Store.getItems().filter(function (i) { return i.track_inventory !== false; });
    if (query) {
      var ql = query.toLowerCase();
      items = items.filter(function (i) { return i.name.toLowerCase().includes(ql); });
    }
    items.sort(function (a, b) {
      var an = !a.expires_at, bn = !b.expires_at;
      if (an && bn) return 0;
      if (an) return 1;
      if (bn) return -1;
      return a.expires_at.localeCompare(b.expires_at);
    });

    if (!items.length) {
      el.innerHTML = '<div class="bg-white rounded-xl border border-gray-100 p-6 text-center text-gray-400 text-sm italic">No items found. Tap <strong>+ Add Item</strong> to get started.</div>';
      return;
    }

    el.innerHTML = items.map(function (item) {
      var lowStockHtml = (item.low_stock_at != null && item.quantity <= item.low_stock_at)
        ? '<span class="ml-1 text-orange-500 font-medium">&middot; Low stock</span>'
        : '';
      return '<div class="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex items-start justify-between gap-3">' +
        '<div class="flex-1 min-w-0">' +
          '<div class="flex items-center gap-2 flex-wrap mb-1">' +
            '<span class="font-semibold text-gray-900 truncate">' + esc(item.name) + '</span>' +
            (item.category ? '<span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">' + esc(item.category) + '</span>' : '') +
          '</div>' +
          '<div class="text-sm text-gray-500 mb-2">' + fmtQty(item.quantity) + ' ' + esc(item.unit) + lowStockHtml + '</div>' +
          expiryBadge(item.expires_at) +
        '</div>' +
        '<div class="flex flex-col items-end gap-2 shrink-0">' +
          '<button data-action="edit" data-id="' + esc(item.id) + '" class="text-xs text-blue-600 font-medium px-3 py-1.5 bg-blue-50 rounded-lg">Edit</button>' +
          '<button data-action="use" data-id="' + esc(item.id) + '"' + (item.quantity <= 0 ? ' disabled' : '') + ' class="text-xs text-gray-600 font-medium px-3 py-1.5 bg-gray-100 rounded-lg disabled:opacity-40">Use 1</button>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  function mealList(dateStr) {
    var el = document.getElementById('meal-list');
    if (!el) return;
    var d = dateStr || (function () {
      var now = new Date();
      var p = function (n) { return String(n).padStart(2, '0'); };
      return now.getFullYear() + '-' + p(now.getMonth() + 1) + '-' + p(now.getDate());
    })();
    var meals = Store.getMealsForDate(d);

    if (!meals.length) {
      el.innerHTML = '<div class="bg-white rounded-xl border border-gray-100 p-6 text-center text-gray-400 text-sm italic">No meals logged for this day. Tap <strong>+ Log Meal</strong> to start.</div>';
      return;
    }

    el.innerHTML = meals.map(function (meal) {
      var colorClass = MEAL_COLORS[meal.meal_type] || 'bg-gray-100 text-gray-600';
      var itemsHtml = (meal.meal_items || []).map(function (mi) {
        return '<li class="text-sm text-gray-700 flex items-center gap-1">' +
          '<span class="w-1.5 h-1.5 bg-green-400 rounded-full shrink-0"></span>' +
          esc(mi.item_name) +
          '<span class="text-gray-400 text-xs">&times; ' + fmtQty(mi.quantity_used) + ' ' + esc(mi.item_unit) + '</span>' +
        '</li>';
      }).join('');
      return '<div class="bg-white rounded-xl border border-gray-100 shadow-sm p-4">' +
        '<div class="flex items-center justify-between mb-2">' +
          '<div class="flex items-center gap-2">' +
            '<span class="text-xs font-semibold px-2 py-1 rounded-full ' + colorClass + '">' + capitalize(meal.meal_type) + '</span>' +
            '<span class="text-xs text-gray-400">' + fmtTime(meal.logged_at) + '</span>' +
          '</div>' +
          '<button data-action="delete-meal" data-id="' + esc(meal.id) + '" data-meal-type="' + esc(meal.meal_type.toLowerCase()) + '" class="text-gray-300 hover:text-red-400 text-xl leading-none">&times;</button>' +
        '</div>' +
        (itemsHtml ? '<ul class="space-y-1 mb-2">' + itemsHtml + '</ul>' : '') +
        (meal.notes ? '<p class="text-xs text-gray-400 italic">' + esc(meal.notes) + '</p>' : '') +
      '</div>';
    }).join('');
  }

  function dashboard() {
    var now = new Date();
    var p = function (n) { return String(n).padStart(2, '0'); };
    var todayStr = now.getFullYear() + '-' + p(now.getMonth() + 1) + '-' + p(now.getDate());

    // Expiring soon
    var expiring = Store.getExpiringItems(7);
    var expiringSeaAll = document.getElementById('expiring-see-all');
    var expiringStrip = document.getElementById('expiring-strip');
    if (expiringSeaAll) {
      expiringSeaAll.innerHTML = expiring.length
        ? '<a href="/inventory" class="text-xs text-green-600 font-medium">See all</a>'
        : '';
    }
    if (expiringStrip) {
      expiringStrip.innerHTML = expiring.length
        ? '<div class="flex flex-col gap-2">' + expiring.map(function (item) {
            return '<a href="/inventory" class="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3 flex items-center justify-between">' +
              '<div>' +
                '<p class="text-sm font-semibold text-gray-900">' + esc(item.name) + '</p>' +
                '<p class="text-xs text-gray-400 mt-0.5">' + fmtQty(item.quantity) + ' ' + esc(item.unit) + ' remaining</p>' +
              '</div>' +
              dashboardExpiryBadge(item.expires_at) +
            '</a>';
          }).join('') + '</div>'
        : '<div class="bg-white rounded-xl border border-gray-100 p-4 text-sm text-gray-400 italic">Nothing expiring in the next 7 days.</div>';
    }

    // Low stock
    var lowStock = Store.getLowStockItems();
    var lowStockSeeAll = document.getElementById('low-stock-see-all');
    var lowStockStrip = document.getElementById('low-stock-strip');
    if (lowStockSeeAll) {
      lowStockSeeAll.innerHTML = lowStock.length
        ? '<a href="/inventory" class="text-xs text-green-600 font-medium">See all</a>'
        : '';
    }
    if (lowStockStrip) {
      lowStockStrip.innerHTML = lowStock.length
        ? '<div class="flex flex-col gap-2">' + lowStock.map(function (item) {
            return '<a href="/inventory" class="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3 flex items-center justify-between">' +
              '<div>' +
                '<p class="text-sm font-semibold text-gray-900">' + esc(item.name) + '</p>' +
                '<p class="text-xs text-gray-400 mt-0.5">' + fmtQty(item.quantity) + ' ' + esc(item.unit) + ' left</p>' +
              '</div>' +
              '<span class="text-xs font-semibold bg-orange-100 text-orange-700 px-2.5 py-1 rounded-full">Restock</span>' +
            '</a>';
          }).join('') + '</div>'
        : '<div class="bg-white rounded-xl border border-gray-100 p-4 text-sm text-gray-400 italic">All stocked up.</div>';
    }

    // Today's meals
    var todaysMeals = Store.getMealsForDate(todayStr);
    var todaysMealsStrip = document.getElementById('todays-meals-strip');
    if (todaysMealsStrip) {
      todaysMealsStrip.innerHTML = todaysMeals.length
        ? '<div class="flex flex-col gap-2">' + todaysMeals.map(function (meal) {
            var colorClass = MEAL_COLORS[meal.meal_type] || 'bg-gray-100 text-gray-600';
            var itemNames = (meal.meal_items || []).map(function (mi) { return esc(mi.item_name); }).join(', ');
            return '<div class="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3">' +
              '<div class="flex items-center gap-2 mb-1.5">' +
                '<span class="text-xs font-semibold px-2 py-0.5 rounded-full ' + colorClass + '">' + capitalize(meal.meal_type) + '</span>' +
                '<span class="text-xs text-gray-400">' + fmtTime(meal.logged_at) + '</span>' +
              '</div>' +
              (itemNames ? '<p class="text-sm text-gray-600">' + itemNames + '</p>' : '') +
            '</div>';
          }).join('') + '</div>'
        : '<div class="bg-white rounded-xl border border-gray-100 p-4 text-sm text-gray-400 italic">No meals logged today.</div>';
    }
  }

  return {
    itemList: itemList,
    mealList: mealList,
    dashboard: dashboard,
  };
})();
