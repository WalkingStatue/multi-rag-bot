import { logger } from './logger';
import { getEnvVar } from '../config/environment';

const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.match(
    /^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/
  )
);

export interface ServiceWorkerConfig {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
  onOfflineReady?: () => void;
  onNeedRefresh?: () => void;
}

export const registerServiceWorker = (config?: ServiceWorkerConfig) => {
  if ('serviceWorker' in navigator) {
    const publicUrl = new URL(getEnvVar.get('VITE_PUBLIC_URL', '') || '', window.location.href);
    if (publicUrl.origin !== window.location.origin) {
      // Our service worker won't work if PUBLIC_URL is on a different origin
      return;
    }

    window.addEventListener('load', () => {
      const swUrl = `${getEnvVar.get('VITE_PUBLIC_URL', '') || ''}/sw.js`;

      if (isLocalhost) {
        // This is running on localhost. Let's check if a service worker still exists or not.
        checkValidServiceWorker(swUrl, config);

        // Add some additional logging to localhost, pointing developers to the
        // service worker/PWA documentation.
        navigator.serviceWorker.ready.then(() => {
          logger.info('This web app is being served cache-first by a service worker');
        });
      } else {
        // Is not localhost. Just register service worker
        registerValidServiceWorker(swUrl, config);
      }
    });
  }
};

const registerValidServiceWorker = (swUrl: string, config?: ServiceWorkerConfig) => {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      logger.info('Service worker registered successfully');

      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (installingWorker == null) {
          return;
        }

        installingWorker.onstatechange = () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // At this point, the updated precached content has been fetched,
              // but the previous service worker will still serve the older
              // content until all client tabs are closed.
              logger.info('New content is available and will be used when all tabs for this page are closed');

              // Execute callback
              if (config && config.onUpdate) {
                config.onUpdate(registration);
              }
            } else {
              // At this point, everything has been precached.
              // It's the perfect time to display a
              // "Content is cached for offline use." message.
              logger.info('Content is cached for offline use');

              // Execute callback
              if (config && config.onSuccess) {
                config.onSuccess(registration);
              }
            }
          }
        };
      };

      // Listen for messages from service worker
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'SYNC_OFFLINE_QUEUE') {
          logger.info('Service worker requested offline queue sync');
          // Trigger offline queue processing
          window.dispatchEvent(new CustomEvent('sw-sync-offline-queue'));
        }
      });

      // Request background sync registration
      if ('sync' in window.ServiceWorkerRegistration.prototype) {
        try {
          (registration as any).sync.register('offline-queue-sync').then(() => {
            logger.info('Background sync registered for offline queue');
          }).catch((error: any) => {
            logger.error(`Failed to register background sync: ${error.message}`);
          });
        } catch (error) {
          logger.error(`Background sync not supported: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }
    })
    .catch((error) => {
      logger.error(`Error during service worker registration: ${error.message}`);
    });
};

const checkValidServiceWorker = (swUrl: string, config?: ServiceWorkerConfig) => {
  // Check if the service worker can be found. If it can't reload the page.
  fetch(swUrl, {
    headers: { 'Service-Worker': 'script' },
  })
    .then((response) => {
      // Ensure service worker exists, and that we really are getting a JS file.
      const contentType = response.headers.get('content-type');
      if (
        response.status === 404 ||
        (contentType != null && contentType.indexOf('javascript') === -1)
      ) {
        // No service worker found. Probably a different app. Reload the page.
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister().then(() => {
            window.location.reload();
          });
        });
      } else {
        // Service worker found. Proceed as normal.
        registerValidServiceWorker(swUrl, config);
      }
    })
    .catch(() => {
      logger.info('No internet connection found. App is running in offline mode');
    });
};

export const unregisterServiceWorker = () => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
        logger.info('Service worker unregistered');
      })
      .catch((error) => {
        logger.error(`Error during service worker unregistration: ${error.message}`);
      });
  }
};

// Utility to check if app is running as PWA
export const isPWA = (): boolean => {
  return window.matchMedia('(display-mode: standalone)').matches ||
         (window.navigator as any).standalone === true ||
         document.referrer.includes('android-app://');
};

// Utility to prompt user to install PWA
export const promptPWAInstall = (): Promise<boolean> => {
  return new Promise((resolve) => {
    let deferredPrompt: any;

    window.addEventListener('beforeinstallprompt', (e) => {
      // Prevent Chrome 67 and earlier from automatically showing the prompt
      e.preventDefault();
      // Stash the event so it can be triggered later.
      deferredPrompt = e;
    });

    if (deferredPrompt) {
      // Show the prompt
      deferredPrompt.prompt();
      // Wait for the user to respond to the prompt
      deferredPrompt.userChoice.then((choiceResult: { outcome: string }) => {
        if (choiceResult.outcome === 'accepted') {
          logger.info('User accepted the PWA install prompt');
          resolve(true);
        } else {
          logger.info('User dismissed the PWA install prompt');
          resolve(false);
        }
        deferredPrompt = null;
      });
    } else {
      resolve(false);
    }
  });
};

// Check for service worker updates
export const checkForServiceWorkerUpdate = (): Promise<boolean> => {
  return new Promise((resolve) => {
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.getRegistration().then((registration) => {
        if (registration) {
          registration.update().then(() => {
            logger.info('Checked for service worker updates');
            resolve(true);
          }).catch(() => {
            resolve(false);
          });
        } else {
          resolve(false);
        }
      });
    } else {
      resolve(false);
    }
  });
};

// Get service worker registration
export const getServiceWorkerRegistration = (): Promise<ServiceWorkerRegistration | null> => {
  if ('serviceWorker' in navigator) {
    return navigator.serviceWorker.getRegistration().then(registration => registration || null);
  }
  return Promise.resolve(null);
};

export default {
  registerServiceWorker,
  unregisterServiceWorker,
  isPWA,
  promptPWAInstall,
  checkForServiceWorkerUpdate,
  getServiceWorkerRegistration,
};