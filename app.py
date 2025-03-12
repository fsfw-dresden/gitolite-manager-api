from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List

# Initialize FastAPI app
app = FastAPI(
    title="Sample API",
    description="A sample API with POST and PUT endpoints",
    version="0.1.0",
)

# Data models
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tags: List[str] = []

# In-memory database
items_db: Dict[int, Item] = {}
next_id = 1

@app.post("/items/", response_model=Dict[str, int], status_code=201)
async def create_item(item: Item):
    """
    Create a new item with the provided details.
    
    Returns the ID of the newly created item.
    """
    global next_id
    item_id = next_id
    next_id += 1
    items_db[item_id] = item
    return {"id": item_id}

@app.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int):
    """
    Retrieve an item by its ID.
    """
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.get("/items/", response_model=Dict[int, Item])
async def read_all_items():
    """
    Retrieve all items.
    """
    return items_db

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: Item):
    """
    Update an existing item with the provided details.
    """
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id] = item
    return item

@app.delete("/items/{item_id}", response_model=Dict[str, str])
async def delete_item(item_id: int):
    """
    Delete an item by its ID.
    """
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
    return {"message": f"Item {item_id} deleted successfully"}
