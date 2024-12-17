/**
 * @fileoverview This script handles zooming and panning functionality for an image within a container.
 * It can be used as an -- admittedly hacky -- workaround to run custom JavaScript logic in Dash apps,
 * including script that needs to run in response to an app.callback update.
 *
 * The `custom_js_trigger` element is used for communicating to the script from Dash updates that custom JS logic has to be run.
 * When running an app.callback, the `title` attribute of `custom_js_trigger` can be updated (`Output("custom_js_trigger", "title")`) to trigger specific JS code.
 * The mutation on the elements `custom_js_trigger` are observed to detect changes in the `data-dash-is-loading` attribute, which is set by Dash when an element is loading.
 * The specific code that needs to run is determined by the value of the `title` attribute of the `custom_js_trigger` element.
 *
 * Because Dash is slow to add elements to the page as a result of API calls,
 * the script s `waitForElement()` to wait for specific elements to be available in the DOM before attaching event listeners or running other logic on the element.
 * (The DOMContentLoaded event is not sufficient because some elements load faster than others).
 *
 * JS packages can be loaded from CDN in main.py using the `external_scripts` argument of the app object.
 */

/**
 * Custom JS logic
 */

// Script-wide variables used to communicate between scripts that await different elements to load.
let switching_to_other_alert = false;
let panzoomInstance = null;

// Utility function to waits for an element to be available in the DOM before running JS code that depends on the element.
function waitForElement(selector) {
  return new Promise((resolve) => {
    if (document.querySelector(selector)) {
      return resolve(document.querySelector(selector));
    }

    const observer = new MutationObserver((mutations) => {
      if (document.querySelector(selector)) {
        observer.disconnect();
        resolve(document.querySelector(selector));
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  });
}

// Observe mutations of the `custom_js_trigger` element to detect changes in the `data-dash-is-loading` and trigger custon JS as a response.
waitForElement("#custom_js_trigger").then((trigger) => {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "data-dash-is-loading"
      ) {
        if (trigger.title == "reset_zoom") {
          switching_to_other_alert = true;
        }
      }
    });
  });

  observer.observe(trigger, {
    attributes: true,
  });
});

/**
 * Custom JS scripts
 */

// Initializes the Panzoom instance on the container and adjusts the bounding box styling on transform.
waitForElement("#image-container-with-bbox").then((container) => {
  panzoomInstance = panzoom(container, {
    bounds: true,
    boundsPadding: 1,
    minZoom: 1,
    initialX: 0,
    initialY: 0,
    initialZoom: 1,
  });

  panzoomInstance.on("transform", (e) => {
    const transform = panzoomInstance.getTransform();

    const bbox = document.querySelector("#bbox-styling");
    if (bbox) {
      const newThickness = 2 / transform.scale;
      bbox.style.border = `${newThickness}px solid red`;
    }

    if (transform.scale === 1) {
      container.style.transform = "";
    }
  });

  // Resets the zoom level when the main image is loaded.
  waitForElement("#main-image").then((image) => {
    image.onload = () => {
      // Waiting for image to load avoids flicker whereby old image is zoomed out before new image is loaded
      if (switching_to_other_alert) {
        switching_to_other_alert = false;
        panzoomInstance.moveTo(0, 0);
        panzoomInstance.zoomAbs(0, 0, 1);
      }
    };
  });
});
