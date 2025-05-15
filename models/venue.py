from typing import Dict, Any, Optional
from pydantic import BaseModel, create_model


def create_dynamic_model(data_dict: Dict[str, Any], model_name: str = "DynamicModel") -> type[BaseModel]:
    """
    Create a dynamic Pydantic model based on a dictionary data structure
    
    Args:
        data_dict: Dictionary containing sample data
        model_name: Name for the generated model class
        
    Returns:
        A dynamically created Pydantic model class
    """
    # Define field types based on the values in the dictionary
    field_definitions = {}
    
    for key, value in data_dict.items():
        field_type = type(value)
        
        # Handle special cases like empty strings, None values
        if value is None:
            field_definitions[key] = (Optional[str], None)
        elif field_type == str:
            field_definitions[key] = (str, ...)
        elif field_type == int:
            field_definitions[key] = (int, ...)
        elif field_type == float:
            field_definitions[key] = (float, ...)
        elif field_type == bool:
            field_definitions[key] = (bool, ...)
        elif field_type == list:
            field_definitions[key] = (list, ...)
        elif field_type == dict:
            field_definitions[key] = (dict, ...)
        else:
            # Default to string for unknown types
            field_definitions[key] = (str, ...)
    
    # Create the model dynamically
    dynamic_model = create_model(model_name, **field_definitions)
    
    # Add docstring
    dynamic_model.__doc__ = f"Dynamically generated model for {model_name}"
    
    return dynamic_model


class VenueBase(BaseModel):
    """Base model for venue data that defines common behavior"""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model instance from dictionary, ignoring extra fields"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


# Original fixed model - keep for backwards compatibility
class Venue(VenueBase):
    """
    Represents the data structure of a Venue.
    """
    name: str
    location: str
    price: str
    capacity: str
    rating: float
    reviews: int
    description: str
  