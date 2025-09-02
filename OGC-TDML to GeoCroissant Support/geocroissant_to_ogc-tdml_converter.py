import argparse
import json
import os

# Helper functions removed - now using direct JSON parsing

def convert_geocroissant_to_tdml_manual(geocroissant_path, tdml_output_path):
    # Load the GeoCroissant JSON directly
    with open(geocroissant_path, 'r') as f:
        croissant_data = json.load(f)
    
    # Extract basic metadata
    identifier = croissant_data.get('@id', '') or croissant_data.get('id', '') or 'hls_burn_scars_dataset'
    name = croissant_data.get('name', '')
    description = croissant_data.get('description', '')
    if not description:
        description = "No description provided."
    
    # Extract license
    license_ = croissant_data.get('license', '')
    if isinstance(license_, list):
        license_ = license_[0] if license_ else ''
    
    # Extract providers/creators
    providers = []
    creators = croissant_data.get('creator', [])
    if isinstance(creators, list):
        for creator in creators:
            if isinstance(creator, dict):
                provider_name = creator.get('name', '')
                if provider_name:
                    providers.append(provider_name)
            elif isinstance(creator, str):
                providers.append(creator)
    elif isinstance(creators, dict):
        provider_name = creators.get('name', '')
        if provider_name:
            providers.append(provider_name)
    
    # Set default timestamps
    created_time = croissant_data.get('dateCreated', '') or croissant_data.get('created_time', '')
    updated_time = croissant_data.get('dateModified', '') or croissant_data.get('updated_time', '')
    if not created_time:
        created_time = "2025-01-17T00:00:00Z"
    if not updated_time:
        updated_time = "2025-01-17T00:00:00Z"
    
    version = croissant_data.get('version', '1.0')
    
    # Extract recordSet data
    record_sets = croissant_data.get('recordSet', [])
    main_record_set = None
    for rs in record_sets:
        if rs.get('name') == 'hls_burn_scars':
            main_record_set = rs
            break
    
    if not main_record_set:
        raise ValueError("Could not find main recordSet 'hls_burn_scars'")
    
    # Extract fields from the main record set
    fields = main_record_set.get('field', [])
    
    # Extract band information from bandConfiguration
    bands = []
    classes = []
    
    for field in fields:
        field_name = field.get('name', '')
        
        # Extract band configuration
        if 'image' in field_name and 'geocr:bandConfiguration' in field:
            band_config = field['geocr:bandConfiguration']
            total_bands = band_config.get('totalBands', 0)
            
            for i in range(1, total_bands + 1):
                band_key = f'band{i}'
                if band_key in band_config:
                    band_info = band_config[band_key]
                    band_name = band_info.get('name', f'Band {i}')
                    wavelength = band_info.get('wavelength', '')
                    hls_band = band_info.get('hlsBand', '')
                    
                    band_dict = {
                        "name": band_name,
                        "description": f"{band_name} band ({hls_band})",
                        "wavelength": wavelength,
                        "hlsBand": hls_band
                    }
                    bands.append(band_dict)
        
        # Extract class information from classValues
        if 'annotation' in field_name and 'geocr:classValues' in field:
            class_values = field['geocr:classValues']
            for class_id, class_name in class_values.items():
                class_dict = {
                    "key": class_id,
                    "value": class_name
                }
                classes.append(class_dict)
    
    # Extract data statistics
    data_stats = croissant_data.get('geocr:dataStatistics', {})
    total_samples = data_stats.get('totalSamples', 0)
    training_samples = data_stats.get('trainingSamples', 0)
    validation_samples = data_stats.get('validationSamples', 0)
    
    # Build tasks
    tasks = [{
        "type": "AI_EOTask",
        "id": "task_0",
        "name": "Burn Scar Segmentation",
        "description": "Semantic segmentation of burn scars in satellite imagery using HLS data.",
        "inputType": "image",
        "outputType": "mask",
        "taskType": "segmentation"
    }]
    
    # Extract actual file URLs from geocr:fileListing
    data = []
    file_listing = croissant_data.get('geocr:fileListing', {})
    images = file_listing.get('images', {})
    annotations = file_listing.get('annotations', {})
    
    # Process training images and annotations
    train_images = images.get('train', [])
    train_annotations = annotations.get('train', [])
    
    # Process validation images and annotations  
    val_images = images.get('val', [])
    val_annotations = annotations.get('val', [])
    
    # Combine training and validation data
    all_images = train_images + val_images
    all_annotations = train_annotations + val_annotations
    
    # Create data entries with actual URLs
    for i, (img_url, mask_url) in enumerate(zip(all_images, all_annotations)):
        if i >= min(50, total_samples):  # Limit to first 50 for reasonable file size
            break
            
        split = "training" if i < len(train_images) else "validation"
        
        data_entry = {
            "type": "AI_EOTrainingData",
            "id": f"data_{i}",
            "dataUrl": [img_url],
            "labels": [{
                "type": "AI_PixelLabel",
                "imageUrl": [mask_url],
                "imageFormat": ["image/tiff"],
                "class": ""
            }]
        }
        data.append(data_entry)
    
    # Build the complete TDML structure
    tdml_structure = {
        "type": "AI_EOTrainingDataset",
        "id": identifier,
        "name": name,
        "description": description,
        "license": license_,
        "providers": providers,
        "createdTime": created_time,
        "updatedTime": updated_time,
        "version": version,
        "tasks": tasks,
        "classes": classes,
        "bands": bands,
        "data": data,
        "amountOfTrainingData": len(data),
        "numberOfClasses": len(classes),
        "dataStatistics": {
            "totalSamples": total_samples,
            "trainingSamples": training_samples,
            "validationSamples": validation_samples
        }
    }
    
    # Write the TDML JSON file
    with open(tdml_output_path, 'w') as f:
        json.dump(tdml_structure, f, indent=2)
    
    print(f"TDML file written to {tdml_output_path}")
    print(f"Converted dataset: {name}")
    print(f"Total samples: {total_samples}")
    print(f"Classes: {len(classes)}")
    print(f"Bands: {len(bands)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert GeoCroissant JSON to TDML JSON using manual JSON structure building.")
    parser.add_argument("geocroissant_path", help="Path to input GeoCroissant JSON")
    parser.add_argument("tdml_output_path", help="Path to output TDML JSON")
    args = parser.parse_args()
    convert_geocroissant_to_tdml_manual(args.geocroissant_path, args.tdml_output_path) 
