class OfflineManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.syncInProgress = false;
    this.init();
  }

  async init() {
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());

    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/static/js/service-worker.js');
        if ('SyncManager' in window) {
          await registration.sync.register('sync-sales');
        }
      } catch (error) {
        console.error('Service worker registration failed:', error);
      }
    }

    await this.downloadOfflineData();
    if (this.isOnline) {
      await this.syncPendingSales();
    }
  }

  handleOnline() {
    this.isOnline = true;
    this.syncPendingSales();
  }

  handleOffline() {
    this.isOnline = false;
  }

  async downloadOfflineData() {
    if (!this.isOnline) {
      return;
    }

    try {
      const response = await fetch('/sales/offline-data/');
      const data = await response.json();
      if (!data.success) {
        return;
      }

      await window.offlineDB.cacheProducts(data.products || []);
      localStorage.setItem('offline_customers', JSON.stringify(data.customers || []));
      localStorage.setItem('offline_bundles', JSON.stringify(data.bundles || []));
      localStorage.setItem('last_sync', data.sync_time || new Date().toISOString());
    } catch (error) {
      console.error('Download offline data failed:', error);
    }
  }

  async saveSaleOffline(saleData) {
    if (!this.isOnline) {
      const saleId = await window.offlineDB.savePendingSale(saleData);
      const pendingSales = JSON.parse(localStorage.getItem('pending_sales') || '[]');
      pendingSales.push({ id: saleId, data: saleData, timestamp: new Date().toISOString() });
      localStorage.setItem('pending_sales', JSON.stringify(pendingSales));
      return { success: true, offline: true, saleId: saleId };
    }

    try {
      const response = await fetch('/sales/sync-offline/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken')
        },
        body: JSON.stringify({ sales: [saleData] })
      });
      const result = await response.json();
      return { success: Boolean(result.success), offline: false, data: result };
    } catch (error) {
      console.error('Online save failed. Falling back offline', error);
      return this.saveSaleOffline(saleData);
    }
  }

  async syncPendingSales() {
    if (!this.isOnline || this.syncInProgress) {
      return;
    }

    const pendingSales = JSON.parse(localStorage.getItem('pending_sales') || '[]');
    if (!pendingSales.length) {
      return;
    }

    this.syncInProgress = true;
    try {
      const response = await fetch('/sales/sync-offline/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken')
        },
        body: JSON.stringify({ sales: pendingSales.map((sale) => sale.data) })
      });
      const result = await response.json();

      if (result.success) {
        for (const sale of pendingSales) {
          await window.offlineDB.markAsSynced(sale.id);
        }
        localStorage.setItem('pending_sales', '[]');
      }
    } catch (error) {
      console.error('Sync pending sales failed:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  async getOfflineProducts() {
    let products = await window.offlineDB.getCachedProducts();
    if (!products.length && this.isOnline) {
      await this.downloadOfflineData();
      products = await window.offlineDB.getCachedProducts();
    }
    return products;
  }

  getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i += 1) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === `${name}=`) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
}

window.offlineManager = new OfflineManager();
