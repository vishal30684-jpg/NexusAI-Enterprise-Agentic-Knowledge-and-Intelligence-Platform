
from uuid import uuid4

from backend.services.chunker import split_pages
from backend.models import (
    Document,
    DocumentChunk,
    DocumentPermission,
    User,
)

from backend.services.embedding import generate_embedding
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    status,
)
from backend.services.document_parser import extract_pages_from_document
from sqlalchemy.orm import Session
from pathlib import Path
import shutil

from backend.database import get_db

from backend.routers.auth import get_current_user


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user

UPLOAD_DIR = Path("uploads")


@router.get("/")
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Document)

    # Admins can view all documents.
    if current_user.role != "ADMIN":
        query = query.filter(
            (Document.uploaded_by == current_user.id)
            | (
                db.query(DocumentPermission.id)
                .filter(
                    DocumentPermission.document_id == Document.id,
                    DocumentPermission.user_id == current_user.id,
                )
                .exists()
            )
        )

    documents = query.order_by(
        Document.created_at.desc()
    ).all()

    return [
        {
            "id": document.id,
            "filename": document.filename,
            "uploaded_by": document.uploaded_by,
            "created_at": document.created_at.isoformat(),
        }
        for document in documents
    ]


@router.get("/{document_id}/content")
def get_document_content(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Admins can read all documents.
    # Employees can read their own or shared documents.
    if current_user.role != "ADMIN":
        has_access = (
            document.uploaded_by == current_user.id
            or db.query(DocumentPermission.id)
            .filter(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == current_user.id,
            )
            .first()
            is not None
        )

        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this document",
            )

    return {
        "id": document.id,
        "filename": document.filename,
        "content": document.content,
        "uploaded_by": document.uploaded_by,
        "created_at": document.created_at.isoformat(),
    }


@router.post("/{document_id}/permissions/{user_id}")
def grant_document_permission(
    document_id: int,
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    target_user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if target_user.role == "ADMIN":
        raise HTTPException(
            status_code=400,
            detail="Document sharing is only needed for non-admin users"
        )

    existing_permission = (
        db.query(DocumentPermission)
        .filter(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == user_id,
        )
        .first()
    )

    if existing_permission:
        raise HTTPException(
            status_code=409,
            detail="Permission already exists"
        )

    permission = DocumentPermission(
        document_id=document_id,
        user_id=user_id,
        granted_by=current_user.id,
    )

    db.add(permission)
    db.commit()
    db.refresh(permission)

    return {
        "message": "Document access granted successfully",
        "document_id": document_id,
        "user_id": user_id,
        "granted_by": current_user.id,
    }


@router.get("/{document_id}/permissions")
def list_document_permissions(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    permissions = (
        db.query(DocumentPermission, User)
        .join(
            User,
            DocumentPermission.user_id == User.id
        )
        .filter(
            DocumentPermission.document_id == document_id
        )
        .order_by(User.id.asc())
        .all()
    )

    return [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "granted_by": permission.granted_by,
            "granted_at": permission.created_at,
        }
        for permission, user in permissions
    ]


@router.delete("/{document_id}/permissions/{user_id}")
def revoke_document_permission(
    document_id: int,
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    permission = (
        db.query(DocumentPermission)
        .filter(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == user_id,
        )
        .first()
    )

    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Document permission not found"
        )

    db.delete(permission)
    db.commit()

    return {
        "message": "Document access revoked successfully",
        "document_id": document_id,
        "user_id": user_id,
        "revoked_by": current_user.id,
    }


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected"
        )

    allowed_extensions = {".pdf", ".txt", ".md", ".docx", ".csv"}
    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    if not original_filename or extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Allowed formats: PDF, TXT, MD, DOCX, CSV."
        )
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    file_size = 0

    while True:
        chunk = file.file.read(1024 * 1024)  # Read 1 MB at a time

        if not chunk:
            break

        file_size += len(chunk)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum upload size is 10 MB."
            )

    file.file.seek(0)
    stored_filename = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    
    try:
        pages = extract_pages_from_document(str(file_path))
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"Could not process document: {exc}"
        )

    if not pages or not any(page["text"].strip() for page in pages):
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="The document contains no extractable text."
        )


    chunks = split_pages(pages)
    if not chunks:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="No searchable text chunks could be generated."
        )

    extracted_text = "\n".join(
       page["text"]
       for page in pages
    )

    document = Document(
       filename=original_filename,
       file_path=str(file_path),
       uploaded_by=current_user.id,
       content=extracted_text
    )

    
    try:
        db.add(document)
        db.flush()  # Get the document ID without committing yet.

        for index, chunk in enumerate(chunks):
            embedding = generate_embedding(chunk["content"])

            document_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                page_number=chunk["page_number"],
                content=chunk["content"],
                embedding=embedding,
            )

            db.add(document_chunk)

        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Document upload failed while saving the document or its embeddings.",
        )


    return {
        "message": "Document uploaded successfully",
        "document_id": document.id,
        "filename": document.filename,
        "uploaded_by": current_user.id
    }
    
    

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Find the document.
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # 2. Check ownership. Admins can delete any document.
    if (
        current_user.role != "ADMIN"
        and document.uploaded_by != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot delete another user's document",
        )

    # 3. Remember the file path before deleting the database row.
    file_path = Path(document.file_path)

    try:
        # 4. Delete dependent rows first because the chunk
        #    foreign key does not currently specify CASCADE.
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete(synchronize_session=False)

        db.query(DocumentPermission).filter(
            DocumentPermission.document_id == document_id
        ).delete(synchronize_session=False)

        # 5. Delete the document record.
        db.delete(document)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Document deletion failed",
        )

    # 6. Remove the stored file after the database commit.
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Document data was deleted, but the stored file "
                "could not be removed. Contact an administrator."
            ),
        )

    return {
        "message": "Document deleted successfully",
        "document_id": document_id,
    }
    