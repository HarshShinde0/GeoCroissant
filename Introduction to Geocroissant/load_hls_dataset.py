import os
import json
from glob import glob
from datasets import Dataset, DatasetDict
import datasets

def load_hls_burn_scars_dataset():
    """Load HLS Burn Scars dataset from local files"""
    
    # Dataset path
    dataset_path = "/teamspace/studios/this_studio/ZOO-AI-DATASET-MAAS/Introduction to Geocroissant/hls_burn_scars"
    
    def get_file_pairs(split):
        """Get image and annotation file pairs for a split"""
        split_path = os.path.join(dataset_path, split)
        image_files = glob(os.path.join(split_path, "*_merged.tif"))
        
        pairs = []
        for img_file in image_files:
            mask_file = img_file.replace("_merged.tif", ".mask.tif")
            if os.path.exists(mask_file):
                pairs.append({
                    "image": img_file,
                    "annotation": mask_file
                })
        
        return pairs
    
    # Load training and validation data
    train_data = get_file_pairs("training")
    val_data = get_file_pairs("validation")
    
    print(f"Found {len(train_data)} training samples")
    print(f"Found {len(val_data)} validation samples")
    
    # Create datasets
    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)
    
    # Create dataset dictionary
    dataset_dict = DatasetDict({
        "train": train_dataset,
        "validation": val_dataset
    })
    
    return dataset_dict

if __name__ == "__main__":
    dataset = load_hls_burn_scars_dataset()
