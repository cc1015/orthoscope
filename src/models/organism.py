from enum import Enum

class Organism(Enum):
    """
    Represents an organism.
    """
    HUMAN = ('Homo sapiens', 9606)
    MOUSE = ('Mus musculus', 10090)
    ALPACA = ('Vicugna pacos', 30538)
    CYNO = ('Macaca fascicularis', 9541)
    CHICKEN = ('Gallus gallus', 9031)
    RABBIT = ('Oryctolagus cuniculus', 9986)
    LLAMA = ('Lama glama', 9844)
    
    @property
    def tax_id(self):
        return self.value[1]


class CustomOrganism:
    """
    Represents a custom organism provided by the user.
    Mimics the Organism enum interface for compatibility.
    """
    def __init__(self, scientific_name: str, tax_id: int):
        """
        Initialize a custom organism.
        
        Args:
            scientific_name: The scientific name of the organism (e.g., "Canis lupus")
            tax_id: The NCBI taxonomic ID (e.g., 9615)
        """
        self._scientific_name = scientific_name
        self._tax_id = tax_id
        # Generate a name from scientific name (e.g., "Canis lupus" -> "CANIS_LUPUS")
        self._name = scientific_name.upper().replace(' ', '_')
    
    @property
    def name(self):
        """Returns the organism name (similar to enum name)."""
        return self._name
    
    @property
    def tax_id(self):
        """Returns the taxonomic ID."""
        return self._tax_id
    
    @property
    def value(self):
        """Returns a tuple (scientific_name, tax_id) to mimic enum value."""
        return (self._scientific_name, self._tax_id)
    
    def __eq__(self, other):
        """Equality comparison."""
        if isinstance(other, CustomOrganism):
            return self._tax_id == other._tax_id
        return False
    
    def __hash__(self):
        """Hash for use in dictionaries."""
        return hash((self._scientific_name, self._tax_id))
    
    def __repr__(self):
        return f"CustomOrganism({self._scientific_name}, {self._tax_id})"