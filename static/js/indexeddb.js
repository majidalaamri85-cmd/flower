class OfflineDatabase {
  constructor() {
    this.dbName = 'ShopManagementDB';
    this.version = 1;
    this.db = null;
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        if (!db.objectStoreNames.contains('pending_sales')) {
          const saleStore = db.createObjectStore('pending_sales', { keyPath: 'id', autoIncrement: true });
          saleStore.createIndex('timestamp', 'timestamp', { unique: false });
          saleStore.createIndex('synced', 'synced', { unique: false });
        }

        if (!db.objectStoreNames.contains('products_cache')) {
          const productStore = db.createObjectStore('products_cache', { keyPath: 'id' });
          productStore.createIndex('type', 'type', { unique: false });
        }

        if (!db.objectStoreNames.contains('customers_cache')) {
          db.createObjectStore('customers_cache', { keyPath: 'id' });
        }
      };
    });
  }

  async savePendingSale(saleData) {
    const transaction = this.db.transaction(['pending_sales'], 'readwrite');
    const store = transaction.objectStore('pending_sales');
    saleData.timestamp = new Date().toISOString();
    saleData.synced = false;

    return new Promise((resolve, reject) => {
      const request = store.add(saleData);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getPendingSales() {
    const transaction = this.db.transaction(['pending_sales'], 'readonly');
    const store = transaction.objectStore('pending_sales');
    const index = store.index('synced');

    return new Promise((resolve, reject) => {
      const request = index.getAll(false);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getSaleById(id) {
    const transaction = this.db.transaction(['pending_sales'], 'readonly');
    const store = transaction.objectStore('pending_sales');

    return new Promise((resolve, reject) => {
      const request = store.get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async markAsSynced(saleId) {
    const sale = await this.getSaleById(saleId);
    if (!sale) {
      return;
    }

    sale.synced = true;
    const transaction = this.db.transaction(['pending_sales'], 'readwrite');
    const store = transaction.objectStore('pending_sales');
    store.put(sale);
  }

  async cacheProducts(products) {
    const transaction = this.db.transaction(['products_cache'], 'readwrite');
    const store = transaction.objectStore('products_cache');
    products.forEach((product) => store.put(product));
  }

  async getCachedProducts() {
    const transaction = this.db.transaction(['products_cache'], 'readonly');
    const store = transaction.objectStore('products_cache');

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
}

window.offlineDB = new OfflineDatabase();
window.offlineDB.init().then(() => {
  console.log('Offline database initialized');
});
