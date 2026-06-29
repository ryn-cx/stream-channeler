import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.items.models import Item
from app.items.schemas import (
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
)
from app.schemas import Message, ReadOptions
from app.service import get_read_results

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
def read_items(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ItemsPublic:
    """
    Retrieve items.
    """
    item_query = select(Item)
    if not current_user.is_superuser:
        item_query = item_query.where(Item.owner_id == current_user.id)

    items, total_count, filtered_count, is_server_side = get_read_results(
        session,
        item_query,
        schema=ItemPublic,
        default_sort=Item.created_at,
        tiebreaker=Item.id,
        params=read_options,
    )

    return ItemsPublic(
        data=[ItemPublic.model_validate(item) for item in items],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


@router.get("/{item_id}", response_model=ItemPublic)
def read_item(
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID,
) -> Item:
    """
    Get item by ID.
    """
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return item


@router.post("/", response_model=ItemPublic)
def create_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_in: ItemCreate,
) -> Item:
    """
    Create new item.
    """
    item = Item.model_validate(item_in, update={"owner_id": current_user.id})
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/{item_id}", response_model=ItemPublic)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID,
    item_in: ItemUpdate,
) -> Item:
    """
    Update an item.
    """
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    update_dict = item_in.model_dump(exclude_unset=True)
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_item(
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID,
) -> Message:
    """
    Delete an item.
    """
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    session.delete(item)
    session.commit()
    return Message(message="Item deleted successfully")
