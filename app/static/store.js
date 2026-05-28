window.Store = (function () {
  var ITEMS_KEY = 'food_inventory_items';
  var MEALS_KEY = 'food_inventory_meals';

  function getItems() {
    try { return JSON.parse(localStorage.getItem(ITEMS_KEY) || '[]'); }
    catch (e) { return []; }
  }

  function saveItems(items) {
    localStorage.setItem(ITEMS_KEY, JSON.stringify(items));
  }

  function getMeals() {
    try { return JSON.parse(localStorage.getItem(MEALS_KEY) || '[]'); }
    catch (e) { return []; }
  }

  function saveMeals(meals) {
    localStorage.setItem(MEALS_KEY, JSON.stringify(meals));
  }

  function localIso() {
    var d = new Date();
    var p = function (n) { return String(n).padStart(2, '0'); };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) +
      'T' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  function localDate() {
    var d = new Date();
    var p = function (n) { return String(n).padStart(2, '0'); };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }

  function createItem(data) {
    var items = getItems();
    var ts = localIso();
    var item = {
      id: crypto.randomUUID(),
      name: (data.name || '').trim(),
      category: (data.category || '').trim() || null,
      quantity: parseFloat(data.quantity) || 1,
      unit: ((data.unit || 'units').trim()) || 'units',
      bought_at: data.bought_at || localDate(),
      expires_at: data.expires_at || null,
      low_stock_at: data.low_stock_at ? parseFloat(data.low_stock_at) : null,
      track_inventory: true,
      created_at: ts,
      updated_at: ts,
    };
    items.push(item);
    saveItems(items);
    return item;
  }

  function updateItem(id, data) {
    var items = getItems();
    var item = items.find(function (i) { return i.id === id; });
    if (!item) return null;
    if (data.name !== undefined) item.name = (data.name || '').trim();
    if (data.category !== undefined) item.category = (data.category || '').trim() || null;
    if (data.quantity !== undefined) item.quantity = parseFloat(data.quantity) || 0;
    if (data.unit !== undefined) item.unit = ((data.unit || 'units').trim()) || 'units';
    if (data.bought_at !== undefined) item.bought_at = data.bought_at || null;
    if (data.expires_at !== undefined) item.expires_at = data.expires_at || null;
    if (data.low_stock_at !== undefined) item.low_stock_at = data.low_stock_at ? parseFloat(data.low_stock_at) : null;
    item.updated_at = localIso();
    saveItems(items);
    return item;
  }

  function deleteItem(id) {
    saveItems(getItems().filter(function (i) { return i.id !== id; }));
  }

  function useItem(id) {
    var items = getItems();
    var item = items.find(function (i) { return i.id === id; });
    if (item && item.quantity > 0) {
      item.quantity = Math.max(0, Math.round((item.quantity - 1) * 100) / 100);
      item.updated_at = localIso();
      saveItems(items);
    }
    return item;
  }

  function createMeal(data) {
    var items = getItems();
    var meals = getMeals();
    var ts = localIso();
    var entries = [];
    try {
      entries = typeof data.items_json === 'string'
        ? JSON.parse(data.items_json)
        : (data.items_json || []);
    } catch (e) {}

    var mealItems = [];
    for (var i = 0; i < entries.length; i++) {
      var entry = entries[i];
      var qty = Math.max(0.1, parseFloat(entry.quantity) || 1);
      var item_id = entry.id || null;

      if (item_id) {
        var invItem = items.find(function (it) { return it.id === item_id; });
        if (invItem) {
          invItem.quantity = Math.max(0, Math.round((invItem.quantity - qty) * 100) / 100);
          invItem.updated_at = ts;
          mealItems.push({ item_id: item_id, item_name: invItem.name, item_unit: invItem.unit, quantity_used: qty });
        }
      } else if (entry.name && (entry.track_inventory === true || entry.track_inventory === 'true')) {
        var newItem = {
          id: crypto.randomUUID(),
          name: (entry.name || '').trim(),
          category: null,
          quantity: 0,
          unit: (entry.unit || 'units'),
          bought_at: localDate(),
          expires_at: null,
          low_stock_at: null,
          track_inventory: true,
          created_at: ts,
          updated_at: ts,
        };
        items.push(newItem);
        mealItems.push({ item_id: newItem.id, item_name: newItem.name, item_unit: newItem.unit, quantity_used: qty });
      } else if (entry.name) {
        mealItems.push({ item_id: null, item_name: (entry.name || '').trim(), item_unit: (entry.unit || 'units'), quantity_used: qty });
      }
    }

    var d = new Date();
    var p = function (n) { return String(n).padStart(2, '0'); };
    var loggedAt = data.meal_date
      ? data.meal_date + 'T' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':00'
      : ts;

    var meal = {
      id: crypto.randomUUID(),
      meal_type: (data.meal_type || 'BREAKFAST').toUpperCase(),
      logged_at: loggedAt,
      notes: (data.notes || '').trim() || null,
      created_at: ts,
      meal_items: mealItems,
    };

    meals.push(meal);
    saveItems(items);
    saveMeals(meals);
    return meal;
  }

  function deleteMeal(id) {
    var meals = getMeals();
    var meal = meals.find(function (m) { return m.id === id; });
    if (!meal) return;
    if (meal.meal_items) {
      var items = getItems();
      for (var i = 0; i < meal.meal_items.length; i++) {
        var mi = meal.meal_items[i];
        if (mi.item_id) {
          var item = items.find(function (it) { return it.id === mi.item_id; });
          if (item) {
            item.quantity = Math.round((item.quantity + mi.quantity_used) * 100) / 100;
            item.updated_at = localIso();
          }
        }
      }
      saveItems(items);
    }
    saveMeals(meals.filter(function (m) { return m.id !== id; }));
  }

  function getMealsForDate(dateStr) {
    return getMeals().filter(function (m) { return m.logged_at && m.logged_at.startsWith(dateStr); });
  }

  function getExpiringItems(days) {
    var cutoff = new Date();
    cutoff.setDate(cutoff.getDate() + days);
    var p = function (n) { return String(n).padStart(2, '0'); };
    var cutoffStr = cutoff.getFullYear() + '-' + p(cutoff.getMonth() + 1) + '-' + p(cutoff.getDate());
    return getItems().filter(function (i) {
      return i.track_inventory !== false && i.expires_at && i.expires_at <= cutoffStr && i.quantity > 0;
    }).sort(function (a, b) { return a.expires_at.localeCompare(b.expires_at); });
  }

  function getLowStockItems() {
    return getItems().filter(function (i) {
      return i.track_inventory !== false && i.low_stock_at != null && i.quantity <= i.low_stock_at;
    }).sort(function (a, b) { return a.name.localeCompare(b.name); });
  }

  function getRecentMealItemsJson(days, mealType) {
    var cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    var cutoffStr = cutoff.toISOString().slice(0, 10) + 'T00:00:00';
    var totals = {};
    getMeals().forEach(function (m) {
      if (m.logged_at < cutoffStr) return;
      if (mealType && m.meal_type !== mealType.toUpperCase()) return;
      (m.meal_items || []).forEach(function (mi) {
        if (!totals[mi.item_name]) totals[mi.item_name] = 0;
        totals[mi.item_name] += mi.quantity_used;
      });
    });
    return JSON.stringify(Object.entries(totals).map(function (e) {
      return { name: e[0], quantity_used: Math.round(e[1] * 10) / 10 };
    }));
  }

  function getExpiringItemsJson(days) {
    return JSON.stringify(getExpiringItems(days).map(function (i) {
      return { name: i.name, expires_at: i.expires_at, quantity: i.quantity, unit: i.unit };
    }));
  }

  function getConsumptionJson() {
    var cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 30);
    var cutoffStr = cutoff.toISOString().slice(0, 10) + 'T00:00:00';
    var items = getItems();
    var totals = {};
    getMeals().forEach(function (m) {
      if (m.logged_at < cutoffStr) return;
      (m.meal_items || []).forEach(function (mi) {
        if (!mi.item_id) return;
        var item = items.find(function (i) { return i.id === mi.item_id; });
        if (!item || item.track_inventory === false) return;
        if (!totals[mi.item_id]) {
          totals[mi.item_id] = { name: mi.item_name, unit: mi.item_unit, total: 0, current_quantity: item.quantity };
        }
        totals[mi.item_id].total += mi.quantity_used;
      });
    });
    return JSON.stringify(Object.values(totals).map(function (t) {
      return { name: t.name, unit: t.unit, quantity_used_30d: Math.round(t.total * 10) / 10, current_quantity: t.current_quantity };
    }));
  }

  function getLowStockJson() {
    return JSON.stringify(getLowStockItems().map(function (i) {
      return { name: i.name, quantity: i.quantity, unit: i.unit, low_stock_at: i.low_stock_at };
    }));
  }

  return {
    getItems: getItems,
    saveItems: saveItems,
    getMeals: getMeals,
    saveMeals: saveMeals,
    createItem: createItem,
    updateItem: updateItem,
    deleteItem: deleteItem,
    useItem: useItem,
    createMeal: createMeal,
    deleteMeal: deleteMeal,
    getMealsForDate: getMealsForDate,
    getExpiringItems: getExpiringItems,
    getLowStockItems: getLowStockItems,
    getRecentMealItemsJson: getRecentMealItemsJson,
    getExpiringItemsJson: getExpiringItemsJson,
    getConsumptionJson: getConsumptionJson,
    getLowStockJson: getLowStockJson,
  };
})();
