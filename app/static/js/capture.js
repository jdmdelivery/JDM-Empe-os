(() => {
  const initSignaturePads = () => {
    document.querySelectorAll("[data-signature-pad]").forEach((canvas) => {
      const inputId = canvas.getAttribute("data-target-input");
      const input = inputId ? document.getElementById(inputId) : null;
      const clearBtn = document.querySelector(`[data-clear-signature="${canvas.id}"]`);
      const ctx = canvas.getContext("2d");
      let drawing = false;

      const resize = () => {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        const width = canvas.clientWidth || 320;
        const height = canvas.clientHeight || 160;
        canvas.width = width * ratio;
        canvas.height = height * ratio;
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.strokeStyle = "#1a1030";
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);
      };
      resize();
      window.addEventListener("resize", resize);

      const pos = (event) => {
        const rect = canvas.getBoundingClientRect();
        const point = event.touches ? event.touches[0] : event;
        return { x: point.clientX - rect.left, y: point.clientY - rect.top };
      };

      const start = (event) => {
        drawing = true;
        const p = pos(event);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        event.preventDefault();
      };
      const move = (event) => {
        if (!drawing) return;
        const p = pos(event);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        event.preventDefault();
      };
      const end = () => {
        if (!drawing) return;
        drawing = false;
        if (input) input.value = canvas.toDataURL("image/png");
      };

      canvas.addEventListener("mousedown", start);
      canvas.addEventListener("mousemove", move);
      canvas.addEventListener("mouseup", end);
      canvas.addEventListener("mouseleave", end);
      canvas.addEventListener("touchstart", start, { passive: false });
      canvas.addEventListener("touchmove", move, { passive: false });
      canvas.addEventListener("touchend", end);

      clearBtn?.addEventListener("click", () => {
        resize();
        if (input) input.value = "";
      });
    });
  };

  const initCameraWidgets = () => {
    document.querySelectorAll("[data-camera-widget]").forEach((widget) => {
      const video = widget.querySelector("video");
      const canvas = widget.querySelector("canvas");
      const preview = widget.querySelector("[data-preview]");
      const fileInput = widget.querySelector('input[type="file"]');
      const facing = { current: "environment" };
      let stream = null;

      const stop = () => {
        stream?.getTracks().forEach((t) => t.stop());
        stream = null;
      };

      const startCamera = async (mode) => {
        stop();
        facing.current = mode || facing.current;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: facing.current },
            audio: false,
          });
          video.srcObject = stream;
          await video.play();
          widget.classList.add("camera-open");
        } catch (err) {
          alert("No se pudo abrir la cámara. Puede subir desde la galería.");
        }
      };

      widget.querySelector("[data-open-camera]")?.addEventListener("click", () => startCamera());
      widget.querySelector("[data-front-camera]")?.addEventListener("click", () => startCamera("user"));
      widget.querySelector("[data-rear-camera]")?.addEventListener("click", () => startCamera("environment"));
      widget.querySelector("[data-retake]")?.addEventListener("click", () => {
        preview?.classList.add("d-none");
        startCamera();
      });
      widget.querySelector("[data-capture]")?.addEventListener("click", () => {
        if (!video?.videoWidth) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        canvas.toBlob((blob) => {
          if (!blob || !fileInput) return;
          const file = new File([blob], `captura_${Date.now()}.jpg`, { type: "image/jpeg" });
          const dt = new DataTransfer();
          dt.items.add(file);
          fileInput.files = dt.files;
          if (preview) {
            preview.src = URL.createObjectURL(blob);
            preview.classList.remove("d-none");
          }
          stop();
          widget.classList.remove("camera-open");
        }, "image/jpeg", 0.92);
      });

      fileInput?.addEventListener("change", () => {
        const file = fileInput.files?.[0];
        if (file && preview) {
          preview.src = URL.createObjectURL(file);
          preview.classList.remove("d-none");
        }
      });
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    initSignaturePads();
    initCameraWidgets();
  });
})();