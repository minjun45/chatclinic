# Skill Patch Proposal

## Tool
- `carotid_plaque_analysis_tool`

## Purpose
- Segments carotid plaque and vessel in paired longitudinal/transverse B-mode ultrasound HDF5 files and predicts vulnerability class (low-risk RADS 2 vs high-risk RADS 3-4)

## When to use
- Use this tool when the user uploads a `.h5` or `.hdf5` file containing paired carotid ultrasound images
- Use when the user asks about plaque segmentation, vessel segmentation, or vulnerability classification on carotid ultrasound data

## When not to use
- Do not use for DICOM files, CT, or MRI — this tool is carotid B-mode ultrasound only
- Do not use for clinical tables, FHIR, or HL7 messages

## Modality
- medical-image

## Recommended stage
- post-intake

## Depends on
- none

## Approval policy
- approval not required

## Produces
- `segmentation_masks`
- `classification`
