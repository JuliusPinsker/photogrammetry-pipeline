# Test Images for 3D Reconstruction

This directory contains sample test images for validating the reconstruction pipeline.

## Structure

- `sample_images/` - Small set of test images for CI/CD
- Used by automated tests to verify the pipeline functionality

## Usage

These images are automatically used during testing to ensure:
- Upload functionality works
- Image processing pipelines function correctly  
- Reconstruction tools can process basic input
- API endpoints respond appropriately

## Creating Test Images

For CI purposes, test images should be:
- Small file size (< 1MB each)
- Standard formats (JPEG, PNG)
- Contain simple geometric features
- Cover basic camera movements

Example test images could include:
- Simple geometric objects
- Textured surfaces
- Multiple viewpoints of the same object