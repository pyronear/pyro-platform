let switching_to_other_alert = false;
let panzoomInstance = null;

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

// Observes changes to the element with ID 'custom_js_trigger' and sets the flag for switching alerts.
waitForElement("#custom_js_trigger").then((trigger) => {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "data-dash-is-loading"
      ) {
        if (trigger.title == "reset_zoom") {
          // switching_to_other_alert = true;
          panzoomInstance.moveTo(0, 0);
          panzoomInstance.zoomAbs(0, 0, 1);
        }
      }
    });
  });

  observer.observe(trigger, {
    attributes: true,
  });
});

// Resets the zoom level when the main image is loaded.
waitForElement("#main-image").then((image) => {
  image.onload = () => {
    if (switching_to_other_alert) {
      switching_to_other_alert = false;
      panzoomInstance.moveTo(0, 0);
      panzoomInstance.zoomAbs(0, 0, 1);
    }
  };
});

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
});
