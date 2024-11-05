function waitForElm(selector) {
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

    // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  });
}

waitForElm(".zoomable-image").then((image) => {
  console.log("Element is ready");
  console.log(image);

  const container = document.getElementById("image-container-with-bbox");

  const panzoomInstance = panzoom(container, {
    bounds: true,
    boundsPadding: 1,
    minZoom: 1,
    initialX: 0,
    initialY: 0,
    initialZoom: 1,
  });

  panzoomInstance.on("transform", (e) => {
    const transform = panzoomInstance.getTransform();

    console.log(transform.scale);

    const bbox = document.querySelector("#bbox-styling");
    if (bbox) {
      const newThickness = 2 / transform.scale; // Adjust the thickness based on the scale
      bbox.style.border = `${newThickness}px solid red`;
    }

    if (transform.scale === 1) {
      console.log("Transform scale is 1");
      container.style.transform = "";
    }
  });

  //   const container = document.getElementById("image-container");
  //   let zoomLevel = 1;
  //   const zoomIncrement = 0.5;
  //   const maxZoomLevel = 3;

  //   const bboxContainer = document.getElementById("bbox-container");

  //   let isPanning = false;
  //   let startX = 0;
  //   let startY = 0;
  //   let scrollLeft = 0;
  //   let scrollTop = 0;

  //   image.addEventListener("dragstart", (e) => {
  //     e.preventDefault();
  //   });

  //   container.addEventListener("mousedown", (e) => {
  //     console.log("mousedown");

  //     isPanning = true;
  //     startX = e.clientX;
  //     startY = e.clientY;
  //     scrollLeft = container.scrollLeft;
  //     scrollTop = container.scrollTop;
  //     container.style.cursor = "grabbing";
  //   });

  //   container.addEventListener("mouseup", () => {
  //     isPanning = false;
  //     container.style.cursor = "default";
  //   });

  //   container.addEventListener("mouseleave", () => {
  //     isPanning = false;
  //     container.style.cursor = "default";
  //   });

  //   container.addEventListener("mousemove", (e) => {
  //     if (!isPanning) return;
  //     e.preventDefault();
  //     const x = e.clientX - startX;
  //     const y = e.clientY - startY;
  //     container.scrollLeft = scrollLeft - x;
  //     container.scrollTop = scrollTop - y;
  //   });

  //   container.addEventListener("dblclick", (e) => {
  //     // Get container and image dimensions
  //     const rect = container.getBoundingClientRect();
  //     const offsetX = e.clientX - rect.left;
  //     const offsetY = e.clientY - rect.top;

  //     // Calculate new zoom level
  //     zoomLevel = zoomLevel >= maxZoomLevel ? 1 : zoomLevel + zoomIncrement;

  //     // Set transform origin to the double-click location
  //     image.style.transformOrigin = `${(offsetX / rect.width) * 100}% ${
  //       (offsetY / rect.height) * 100
  //     }%`;
  //     image.style.transform = `scale(${zoomLevel})`;

  //     // Use a timeout to ensure the image transformation is applied before updating the bbox
  //     setTimeout(() => {
  //       // Adjust bbox position and size according to the zoom level
  //       const bbox = bboxContainer.querySelector("div");
  //       const bboxRect = bbox.getBoundingClientRect();

  //       const bboxLeft = (bboxRect.left - rect.left) / rect.width;
  //       const bboxTop = (bboxRect.top - rect.top) / rect.height;
  //       const bboxWidth = bboxRect.width / rect.width;
  //       const bboxHeight = bboxRect.height / rect.height;

  //       bbox.style.transformOrigin = `${(offsetX / rect.width) * 100}% ${
  //         (offsetY / rect.height) * 100
  //       }%`;
  //       bbox.style.transform = `scale(${zoomLevel})`;
  //       bbox.style.left = `${bboxLeft * 100}%`;
  //       bbox.style.top = `${bboxTop * 100}%`;
  //       bbox.style.width = `${bboxWidth * 100}%`;
  //       bbox.style.height = `${bboxHeight * 100}%`;
  //     }, 10);
  //   });
});
