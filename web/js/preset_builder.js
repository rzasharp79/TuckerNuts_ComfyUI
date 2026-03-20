import { app } from "../../../scripts/app.js";

app.registerExtension({
  name: "TuckerNuts.PresetBuilder",

  async nodeCreated(node) {
    if (node.comfyClass !== "PresetBuilder") return;

    const presetWidget = node.widgets.find((w) => w.name === "preset_name");
    const modeWidget = node.widgets.find((w) => w.name === "mode");
    if (!presetWidget || !modeWidget) return;

    let populating = false;

    async function populateFromPreset() {
      if (populating) return;
      const presetName = presetWidget.value;
      const mode = modeWidget.value;

      if (mode !== "edit" || presetName === "New Preset") return;

      try {
        populating = true;
        const resp = await fetch(
          `/tuckernuts/preset/${encodeURIComponent(presetName)}`
        );
        if (!resp.ok) return;
        const data = await resp.json();

        for (const w of node.widgets) {
          if (w.name in data) {
            w.value = data[w.name];
          }
        }
        app.graph.setDirtyCanvas(true, true);
      } catch (e) {
        console.warn("[PresetBuilder] Failed to load preset:", e);
      } finally {
        populating = false;
      }
    }

    // Hook into widget value changes via callback chaining
    const origPresetCb = presetWidget.callback;
    presetWidget.callback = function (...args) {
      if (origPresetCb) origPresetCb.apply(this, args);
      populateFromPreset();
    };

    const origModeCb = modeWidget.callback;
    modeWidget.callback = function (...args) {
      if (origModeCb) origModeCb.apply(this, args);
      populateFromPreset();
    };
  },
});
