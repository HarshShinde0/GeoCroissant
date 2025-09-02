import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Built-in pytdml fix - no external imports needed
class TrainingDataset:
    """Training dataset class that matches pytdml interface"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.name = data.get('name', '')
        self.amount_of_training_data = data.get('amountOfTrainingData', 0)
        self.number_of_classes = data.get('numberOfClasses', 0)
        self.description = data.get('description', '')
        self.license = data.get('license', '')
        self.providers = data.get('providers', [])
        self.created_time = data.get('createdTime', '')
        self.updated_time = data.get('updatedTime', '')
        self.version = data.get('version', '')
        self.tasks = data.get('tasks', [])
        self.classes = data.get('classes', [])
        self.bands = data.get('bands', [])
        self.data = data.get('data', [])
        self.data_statistics = data.get('dataStatistics', {})

class TrainingData:
    """Training data class that matches pytdml interface"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.id = data.get('id', '')
        self.data_url = data.get('dataUrl', [])
        self.labels = data.get('labels', [])

class PixelLabel:
    """Pixel label class that matches pytdml interface"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.image_url = data.get('imageUrl', [])
        self.image_format = data.get('imageFormat', [])
        self.class_name = data.get('class', '')

class EOTask:
    """EO Task class that matches pytdml interface"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.id = data.get('id', '')
        self.name = data.get('name', '')
        self.description = data.get('description', '')
        self.input_type = data.get('inputType', '')
        self.output_type = data.get('outputType', '')
        self.task_type = data.get('taskType', '')

class PytdmlIO:
    """IO class that matches pytdml.io interface"""
    
    @staticmethod
    def read_from_json(file_path: str) -> TrainingDataset:
        """Read TDML JSON file and return TrainingDataset object"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return TrainingDataset(data)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file: {e}")

class Pytdml:
    """Main pytdml class that matches pytdml interface"""
    
    def __init__(self):
        self.io = PytdmlIO()

# Replace the problematic pytdml modules
sys.modules['pytdml'] = Pytdml()
sys.modules['pytdml.io'] = PytdmlIO()

def convert_geocroissant_to_tdml_manual(geocroissant_path, tdml_output_path):
    """
    Convert GeoCroissant JSON to OGC-TDML JSON format with proper field handling.
    """
    try:
        # Load the GeoCroissant JSON directly
        with open(geocroissant_path, 'r') as f:
            croissant_data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"GeoCroissant file not found: {geocroissant_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in GeoCroissant file: {e}")
    
    # Extract basic metadata with proper fallbacks
    identifier = croissant_data.get('@id', '') or croissant_data.get('id', '') or 'hls_burn_scars_dataset'
    name = croissant_data.get('name', 'HLS_Burn_Scars')
    description = croissant_data.get('description', '')
    if not description:
        description = "No description provided."
    
    # Extract license with proper handling
    license_ = croissant_data.get('license', '')
    if isinstance(license_, list):
        license_ = license_[0] if license_ else ''
    if not license_:
        license_ = "https://creativecommons.org/licenses/by/4.0/"
    
    # Extract providers/creators with improved handling
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
    
    # Ensure we have at least one provider
    if not providers:
        providers = ["IBM-NASA Prithvi Models Family"]
    
    # Set default timestamps with proper ISO format
    created_time = croissant_data.get('dateCreated', '') or croissant_data.get('created_time', '')
    updated_time = croissant_data.get('dateModified', '') or croissant_data.get('updated_time', '')
    if not created_time:
        created_time = "2025-01-17T00:00:00Z"
    if not updated_time:
        updated_time = "2025-01-17T00:00:00Z"
    
    version = croissant_data.get('version', '1.0.0')
    
    # Extract recordSet data with improved error handling
    record_sets = croissant_data.get('recordSet', [])
    main_record_set = None
    
    # Try to find the main record set by name or use the first one
    for rs in record_sets:
        if rs.get('name') == 'hls_burn_scars' or 'hls' in rs.get('name', '').lower():
            main_record_set = rs
            break
    
    if not main_record_set and record_sets:
        main_record_set = record_sets[0]  # Use first record set as fallback
        print(f"Warning: Using first record set '{main_record_set.get('name', 'unknown')}' as main record set")
    
    if not main_record_set:
        raise ValueError("Could not find any recordSet in the GeoCroissant data")
    
    # Extract fields from the main record set
    fields = main_record_set.get('field', [])
    
    # Extract band information from geocr:sensorCharacteristics
    bands = []
    classes = []
    
    # Extract band configuration from geocr:sensorCharacteristics
    sensor_characteristics = croissant_data.get('geocr:sensorCharacteristics', [])
    if sensor_characteristics and len(sensor_characteristics) > 0:
        band_config = sensor_characteristics[0].get('bandConfiguration', {})
        if band_config:
            for band_key, band_info in band_config.items():
                if band_key.startswith('band'):
                    band_name = band_info.get('name', f'Band {band_key}')
                    wavelength = band_info.get('wavelength', '')
                    hls_band = band_info.get('hlsBand', '')
                    
                    band_dict = {
                        "name": band_name,
                        "description": f"{band_name} band ({hls_band})",
                        "wavelength": wavelength,
                        "hlsBand": hls_band
                    }
                    bands.append(band_dict)
    
    # Extract class information from geocr:mlTask
    ml_task = croissant_data.get('geocr:mlTask', {})
    if ml_task and 'classes' in ml_task:
        class_list = ml_task['classes']
        if isinstance(class_list, list):
            # Map class names to their expected keys
            class_mapping = {
                "NotBurned": "0",
                "BurnScar": "1", 
                "NoData": "-1"
            }
            for class_name in class_list:
                class_key = class_mapping.get(class_name, str(len(classes)))
                class_dict = {
                    "key": class_key,
                    "value": class_name
                }
                classes.append(class_dict)
    
    # If no classes found, use default burn scar classes
    if not classes:
        classes = [
            {"key": "0", "value": "NotBurned"},
            {"key": "1", "value": "BurnScar"},
            {"key": "-1", "value": "NoData"}
        ]
        print("Warning: No classes found in GeoCroissant data, using default burn scar classes")
    
    # If no bands found, use default HLS bands
    if not bands:
        bands = [
            {"name": "Blue", "description": "Blue band (B02)", "wavelength": "490nm", "hlsBand": "B02"},
            {"name": "Green", "description": "Green band (B03)", "wavelength": "560nm", "hlsBand": "B03"},
            {"name": "Red", "description": "Red band (B04)", "wavelength": "665nm", "hlsBand": "B04"},
            {"name": "NIR", "description": "NIR band (B8A)", "wavelength": "865nm", "hlsBand": "B8A"},
            {"name": "SW1", "description": "SW1 band (B11)", "wavelength": "1610nm", "hlsBand": "B11"},
            {"name": "SW2", "description": "SW2 band (B12)", "wavelength": "2190nm", "hlsBand": "B12"}
        ]
        print("Warning: No bands found in GeoCroissant data, using default HLS bands")
    
    # Extract data statistics with improved handling
    data_stats = croissant_data.get('geocr:dataStatistics', {})
    total_samples = data_stats.get('totalSamples', 0)
    training_samples = data_stats.get('trainingSamples', 0)
    validation_samples = data_stats.get('validationSamples', 0)
    
    # Build tasks with proper structure
    tasks = [{
        "type": "EOTask",
        "id": "task_0",
        "name": "Burn Scar Segmentation",
        "description": "Semantic segmentation of burn scars in satellite imagery using HLS data.",
        "inputType": "image",
        "outputType": "mask",
        "taskType": "segmentation"
    }]
    
    # Extract actual file URLs from geocr:fileListing with improved handling
    data = []
    file_listing = croissant_data.get('geocr:fileListing', {})
    
    if not file_listing:
        print("Warning: No file listing found in GeoCroissant data")
        # Create empty data structure
        data = []
    else:
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
        
        # Ensure we have matching image and annotation pairs
        min_pairs = min(len(all_images), len(all_annotations))
        if min_pairs == 0:
            print("Warning: No image-annotation pairs found in file listing")
        else:
            # Create data entries with actual URLs
            max_samples = min(50, total_samples) if total_samples > 0 else min(50, min_pairs)
            
            for i in range(min(max_samples, min_pairs)):
                img_url = all_images[i]
                mask_url = all_annotations[i]
                
                # Validate URLs
                if not img_url or not mask_url:
                    print(f"Warning: Skipping data entry {i} due to missing URL")
                    continue
                
                data_entry = {
                    "type": "EOTrainingData",
                    "id": f"data_{i}",
                    "dataUrl": [img_url],
                    "labels": [{
                        "type": "PixelLabel",
                        "imageUrl": [mask_url],
                        "imageFormat": ["image/tiff"],
                        "class": ""
                    }]
                }
                data.append(data_entry)
    
    # Build the complete TDML structure with proper field names
    tdml_structure = {
        "type": "EOTrainingDataset",
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
    
    # Validate required fields
    required_fields = ["type", "id", "name", "description", "license", "providers", "createdTime", "updatedTime", "version", "tasks", "classes", "bands", "data"]
    missing_fields = [field for field in required_fields if not tdml_structure.get(field)]
    
    if missing_fields:
        print(f"Warning: Missing required fields: {missing_fields}")
    
    # Write the TDML JSON file with proper error handling
    try:
        with open(tdml_output_path, 'w') as f:
            json.dump(tdml_structure, f, indent=2, ensure_ascii=False)
        
        print(f"TDML file written to {tdml_output_path}")
        print(f"Converted dataset: {name}")
        print(f"Total samples: {total_samples}")
        print(f"Training samples: {training_samples}")
        print(f"Validation samples: {validation_samples}")
        print(f"Classes: {len(classes)}")
        print(f"Bands: {len(bands)}")
        print(f"Data entries: {len(data)}")
        
    except Exception as e:
        raise IOError(f"Failed to write TDML file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert GeoCroissant JSON to TDML JSON using manual JSON structure building.")
    parser.add_argument("geocroissant_path", help="Path to input GeoCroissant JSON")
    parser.add_argument("tdml_output_path", help="Path to output TDML JSON")
    args = parser.parse_args()
    convert_geocroissant_to_tdml_manual(args.geocroissant_path, args.tdml_output_path) 
