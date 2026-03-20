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

      if (presetName === "New Preset") {
        modeWidget.value = "save";
        app.graph.setDirtyCanvas(true, true);
        return;
      }

      // Selecting a real preset switches to edit mode and loads values
      modeWidget.value = "edit";

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

    // Hook into preset_name widget changes
    const origPresetCb = presetWidget.callback;
    presetWidget.callback = function (...args) {
      if (origPresetCb) origPresetCb.apply(this, args);
      populateFromPreset();
    };
  },
});
