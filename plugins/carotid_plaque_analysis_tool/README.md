# carotid_plaque_analysis_tool

Segments carotid plaque and vessel in paired longitudinal/transverse B-mode ultrasound HDF5 files, and predicts vulnerability class (RADS 2 vs RADS 3-4).

Based on team lpsib's solution for the ISBI CSV 2026 Challenge (Carotid Plaque Segmentation and Vulnerability Assessment Challenge). For detailed model architecture, training pipeline, and challenge results, refer to the [original repository](https://github.com/lyyek/CSV2026).

## Dependencies

```
torch>=2.1.0
torchvision>=0.16.0
timm>=0.9.12
h5py>=3.8.0
numpy>=1.24.0
segmentation-models-pytorch>=0.3.3
```

GPU recommended. CPU inference is supported but slow (~30s per case).

## Weights

Model weights are included at `weights/best.pth` inside the plugin directory.

To use a custom checkpoint, set `MODEL_PATH` in `.env`:

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `MODEL_PATH` | Path to the trained `.pth` checkpoint | `weights/best.pth` inside plugin |

## Input format (`input.json`)

```json
{
  "source_path": "/path/to/file.h5",
  "file_name": "1194.h5",
  "suffix": "h5",
  "cls_threshold": 0.8,
  "resize_target": 512
}
```

The HDF5 file must contain:
- `long_img`: longitudinal B-mode image `(H, W)` or `(H, W, 1)`, uint8 or float
- `trans_img`: transverse B-mode image `(H, W)` or `(H, W, 1)`, uint8 or float

## Output artifacts

| Artifact | Description |
|---|---|
| `segmentation_masks` | Longitudinal and transverse masks — `0` background, `1` plaque, `2` vessel |
| `classification` | RADS prediction: `0` = low-risk (RADS 2), `1` = high-risk (RADS 3-4) |

## Limitations

- Trained on the CSV2026 challenge dataset (carotid ultrasound only)
- Not validated for other ultrasound scanners or imaging protocols
- Classification threshold default (0.8) is tuned for the challenge test set
