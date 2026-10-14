
const API_BASE_URL = "http://127.0.0.1:8000";

const historyButton = document.getElementById("history-btn");
let allDocuments = [];
const conversationHistory = document.getElementById("conversation-history");



async function loadChatHistory() {
    if (!accessToken) {
        conversationHistory.textContent = "Please log in to view chat history.";
        return;
    }

    conversationHistory.textContent = "Loading conversations...";

    try {
        const response = await fetch(`${API_BASE_URL}/conversations`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${accessToken}`
            }
        });

        if (!response.ok) {
            throw new Error("Could not load conversations.");
        }

        const conversations = await response.json();
        conversationHistory.replaceChildren();

        if (conversations.length === 0) {
            conversationHistory.textContent = "No saved conversations yet.";
            return;
        }

        conversations.forEach((conversation) => {
            const item = document.createElement("div");
            item.className = "conversation-item";

            const openButton = document.createElement("button");
            openButton.type = "button";
            openButton.className = "sidebar-item";
            openButton.textContent =
                conversation.title || `Conversation ${conversation.id}`;

            openButton.addEventListener("click", () => {
                openConversation(conversation.id);
            });

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "delete-conversation-btn";
            deleteButton.textContent = "🗑️";
            deleteButton.title = "Delete conversation";
            deleteButton.setAttribute("aria-label", "Delete conversation");

            deleteButton.addEventListener("click", () => {
                deleteConversation(conversation.id);
            });

            item.appendChild(openButton);
            item.appendChild(deleteButton);
            conversationHistory.appendChild(item);
        });
    } catch (error) {
        conversationHistory.textContent = error.message;
    }
}

historyButton.addEventListener("click", loadChatHistory);

const documentSearch = document.getElementById("document-search");

documentSearch.addEventListener("input", () => {
    const searchText = documentSearch.value.trim().toLowerCase();

    const documentItems = documentsList.querySelectorAll(".document-item");

    documentItems.forEach((item) => {
        const filename = item.querySelector("h3")?.textContent || "";

        item.hidden = !filename.toLowerCase().includes(searchText);
    });

    const visibleCount = Array.from(documentItems).filter(
        item => !item.hidden
    ).length;

    documentsStatus.textContent = searchText
        ? `${visibleCount} matching document(s) found.`
        : `${allDocuments.length} document(s) found.`;
});




async function openConversation(selectedConversationId) {
    if (!accessToken) return;

    try {
        const response = await fetch(
            `${API_BASE_URL}/conversations/${selectedConversationId}`,
            {
                headers: {
                    "Authorization": `Bearer ${accessToken}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Could not open this conversation.");
        }

        const conversation = await response.json();
        conversationId = conversation.id;
        const messagesContainer = document.getElementById("chat-messages");

        messagesContainer.replaceChildren();

        conversation.messages.forEach((message) => {
            const messageElement = document.createElement("div");
            messageElement.className = `message ${message.role}`;
            messageElement.textContent = message.content;
            messagesContainer.appendChild(messageElement);
        });

        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        alert(error.message);
    }
}


const uploadButton = document.getElementById("upload-btn");
const documentFileInput = document.getElementById("document-file");
const uploadStatus = document.getElementById("upload-status");

uploadButton.addEventListener("click", () => {
    documentFileInput.click();
});


documentFileInput.addEventListener("change", async () => {
    const file = documentFileInput.files[0];

    if (!file) return;

    if (!accessToken) {
        alert("Please log in before uploading a document.");
        documentFileInput.value = "";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        uploadButton.disabled = true;
        uploadButton.textContent = "Uploading...";

        const response = await fetch(
            `${API_BASE_URL}/documents/upload`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${accessToken}`
                },
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Document upload failed."
            );
        }

        uploadStatus.hidden = false;
        uploadStatus.style.color = "green";
        uploadStatus.textContent =
            `✓ ${data.filename} uploaded successfully! (ID: ${data.document_id})`;
    } catch (error) {
        uploadStatus.hidden = false;
        uploadStatus.style.color = "red";
        uploadStatus.textContent = `Upload failed: ${error.message}`;
    } finally {
        uploadButton.disabled = false;
        uploadButton.textContent = "⬆️ Upload document";
        documentFileInput.value = "";
    }
});


const loginForm = document.getElementById("login-form");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const loginButton = document.getElementById("login-btn");
const loginStatus = document.getElementById("login-status");

let accessToken = null;

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginStatus.textContent = "Signing in...";
    loginButton.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
                
            },
            body: JSON.stringify({
                email: loginEmail.value.trim(),
                password: loginPassword.value
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                typeof data.detail === "string"
                    ? data.detail
                    : `Login failed (${response.status})`
            );
        }

        accessToken = data.access_token;
        loadChatHistory();

        if (!accessToken) {
            throw new Error("Login succeeded, but no access token was returned.");
        }


        loginStatus.textContent = "Login successful!";
        loginStatus.style.color = "green";

        // Get the logged-in user's details
        const userResponse = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
                "Authorization": `Bearer ${accessToken}`
            }
        });

        if (!userResponse.ok) {
            throw new Error("Could not fetch user details.");
        }

        const userData = await userResponse.json();

        // Show the user's ID in the top-right corner
        document.getElementById("user-badge").textContent = userData.email;

        // Hide the login card after successful login
        document.getElementById("login-section").style.display = "none";

        await loadChatHistory();
        await loadDocuments();


        console.log("NexusAI login successful.");
        // Load data for the currently logged-in user

    } catch (error) {
        loginStatus.textContent = error.message;
        loginStatus.style.color = "red";
    } finally {
        loginButton.disabled = false;
    }
});


const chatForm = document.getElementById("chat-form");
const questionInput = document.getElementById("question-input");
const chatMessages = document.getElementById("chat-messages");
const sendButton = document.getElementById("send-btn");
const apiStatus = document.getElementById("api-status");
const newChatButton = document.getElementById("new-chat-btn");

const documentsBtn = document.getElementById("documents-btn");
const documentsSection = document.getElementById("documents-section");
const documentsList = document.getElementById("documents-list");
const documentsStatus = document.getElementById("documents-status");
const refreshDocumentsButton = document.getElementById("refresh-documents-btn");



documentsBtn.addEventListener("click", () => {
    chatMessages.style.display = "none";
    chatForm.style.display = "none";

    documentsSection.hidden = false;
    documentsSection.style.display = "block";

    loadDocuments();
});

refreshDocumentsButton.addEventListener("click", () => {
    loadDocuments();
});


let conversationId = null;

// Check whether the backend is running.
async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/openapi.json`);

        if (!response.ok) {
            throw new Error("API unavailable");
        }

        apiStatus.textContent = "Connected";
        document.querySelector(".status-dot").style.background = "#22c55e";
    } catch (error) {
        apiStatus.textContent = "Offline";
        document.querySelector(".status-dot").style.background = "#ef4444";
    }
}


async function loadDocuments() {
    documentsStatus.textContent = "Loading documents...";
    documentsList.replaceChildren();

    try {
        const response = await fetch(`${API_BASE_URL}/documents/`, {
            headers: {
                "Authorization": `Bearer ${accessToken}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || `Failed to load documents (${response.status})`
            );
        }

        if (data.length === 0) {
            documentsStatus.textContent = "No documents found.";
            return;
        }

        documentsStatus.textContent = `${data.length} document(s) found.`;

        data.forEach((doc) => {
            const item = document.createElement("div");
            item.className = "document-item";

            const details = document.createElement("div");

            
            const filename = document.createElement("h3");
            filename.textContent = doc.filename;
            filename.title = "Click to view document";
            filename.style.cursor = "pointer";

            const uploadDate = document.createElement("p");
            uploadDate.textContent =
                `Uploaded: ${new Date(doc.created_at).toLocaleString()}`;

            const documentViewer = document.createElement("div");
            documentViewer.className = "document-viewer";
            documentViewer.hidden = true;

            filename.addEventListener("click", async () => {
                if (!documentViewer.hidden) {
                    documentViewer.hidden = true;
                    return;
                }

                documentViewer.hidden = false;
                documentViewer.textContent = "Loading document...";

                try {
                    const response = await fetch(
                        `${API_BASE_URL}/documents/${doc.id}/content`,
                        {
                            headers: {
                                "Authorization": `Bearer ${accessToken}`
                            }
                        }
                    );

                    const result = await response.json();

                    if (!response.ok) {
                        throw new Error(
                            result.detail || "Failed to load document."
                        );
                    }

                    documentViewer.textContent = result.content || "This document has no readable text.";
                } catch (error) {
                    documentViewer.textContent = error.message;
                }
            });


            
            const manageAccessButton = document.createElement("button");
            manageAccessButton.type = "button";
            manageAccessButton.textContent = "Manage Access";
            manageAccessButton.className = "manage-access-btn";

            
            const permissionPanel = document.createElement("div");
            permissionPanel.className = "permission-panel";
            permissionPanel.hidden = true;

            const permissionStatus = document.createElement("p");
            permissionStatus.textContent = "Click Manage Access to view permissions.";

            permissionPanel.append(permissionStatus);
            

            
            manageAccessButton.addEventListener("click", async () => {
                if (!permissionPanel.hidden) {
                    permissionPanel.hidden = true;
                    return;
                }

                permissionPanel.hidden = false;
                permissionStatus.textContent = "Loading employees...";
                permissionPanel.replaceChildren(permissionStatus);

                try {
                    const [usersResponse, permissionsResponse] = await Promise.all([
                        fetch(`${API_BASE_URL}/auth/users`, {
                            headers: {
                                "Authorization": `Bearer ${accessToken}`
                            }
                        }),
                        fetch(
                            `${API_BASE_URL}/documents/${doc.id}/permissions`,
                            {
                                headers: {
                                    "Authorization": `Bearer ${accessToken}`
                                }
                            }
                        )
                    ]);

                    const usersData = await usersResponse.json();
                    const permissionsData = await permissionsResponse.json();

                    if (!usersResponse.ok) {
                        throw new Error(
                            usersData.detail || "Failed to load employees."
                        );
                    }

                    if (!permissionsResponse.ok) {
                        throw new Error(
                            permissionsData.detail || "Failed to load permissions."
                        );
                    }

                    permissionPanel.replaceChildren();

                    const heading = document.createElement("h4");
                    heading.textContent = "Employee Access";
                    permissionPanel.append(heading);

                    const employees = usersData.filter(
                        user => user.role === "EMPLOYEE"
                    );

                    const permittedUserIds = new Set(
                        permissionsData.map(permission => permission.user_id)
                    );

                    if (employees.length === 0) {
                        permissionStatus.textContent = "No employees found.";
                        permissionPanel.append(permissionStatus);
                        return;
                    }


                    employees.forEach(user => {
                        const hasAccess = permittedUserIds.has(user.id);

                        const employeeRow = document.createElement("div");
                        employeeRow.className = "permission-employee-row";

                        const employeeInfo = document.createElement("p");
                        employeeInfo.textContent =
                            `${user.full_name} (${user.email}) — ` +
                            (hasAccess ? "Access granted" : "No access");

                        const accessButton = document.createElement("button");
                        accessButton.type = "button";
                        accessButton.textContent = hasAccess
                            ? "Revoke Access"
                            : "Grant Access";
                        accessButton.className = hasAccess
                            ? "revoke-access-btn"
                            : "grant-access-btn";

                        accessButton.addEventListener("click", async () => {
                            const grantAccess = !hasAccess;

                            accessButton.disabled = true;
                            accessButton.textContent = "Updating...";

                            try {
                                const permissionResponse = await fetch(
                                    `${API_BASE_URL}/documents/${doc.id}/permissions/${user.id}`,
                                    {
                                        method: grantAccess ? "POST" : "DELETE",
                                        headers: {
                                            "Authorization": `Bearer ${accessToken}`
                                        }
                                    }
                                );

                                const permissionData = await permissionResponse.json();

                                if (!permissionResponse.ok) {
                                    throw new Error(
                                        permissionData.detail || "Failed to update access."
                                    );
                                }

                                // Reload the document's permission panel.
                                permissionPanel.hidden = true;
                                manageAccessButton.click();
                            } catch (error) {
                                alert(error.message);
                                accessButton.disabled = false;
                                accessButton.textContent = grantAccess
                                    ? "Grant Access"
                                    : "Revoke Access";
                            }
                        });

                        const employeeActions = document.createElement("div");
                        employeeActions.className = "permission-employee-actions";
                        employeeActions.append(accessButton);

                        employeeRow.append(employeeInfo, employeeActions);
                        permissionPanel.append(employeeRow);
                    });

                } catch (error) {
                    permissionStatus.textContent = error.message;
                    permissionPanel.replaceChildren(permissionStatus);
                }
            });



            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.textContent = "Delete";
            deleteButton.className = "delete-document-btn";

            deleteButton.addEventListener("click", async () => {
                const confirmed = confirm(
                    `Are you sure you want to permanently delete "${doc.filename}"?`
                );

                if (!confirmed) {
                    return;
                }

                documentsStatus.textContent = `Deleting ${doc.filename}...`;

                try {
                    const deleteResponse = await fetch(
                        `${API_BASE_URL}/documents/${doc.id}`,
                        {
                            method: "DELETE",
                            headers: {
                                "Authorization": `Bearer ${accessToken}`
                            }
                        }
                    );

                    const deleteData = await deleteResponse.json();

                    if (!deleteResponse.ok) {
                        throw new Error(
                            deleteData.detail || "Failed to delete document."
                        );
                    }

                    await loadDocuments();
                } catch (error) {
                    documentsStatus.textContent = error.message;
                }
            });

            item.append(manageAccessButton, deleteButton);
            item.append(permissionPanel);
    

            details.append(filename, uploadDate, documentViewer);
            item.append(details);
            documentsList.append(item);
        });
    } catch (error) {
        documentsStatus.textContent = error.message;
    }
}

// Remove the welcome screen when the first message is sent.
function removeWelcomeScreen() {
    const welcome = document.querySelector(".welcome");

    if (welcome) {
        welcome.remove();
    }
}

// Add a message to the chat.
function addMessage(text, sender) {
    removeWelcomeScreen();

    const message = document.createElement("div");
    message.className = `message ${sender}`;
    message.textContent = text;

    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return message;
}

// Display the sources returned by the backend.
function addSources(sources) {
    if (!Array.isArray(sources) || sources.length === 0) {
        return;
    }

    const section = document.createElement("div");
    section.className = "sources";

    const heading = document.createElement("strong");
    heading.textContent = "Sources";
    section.appendChild(heading);

    const list = document.createElement("ul");

    sources.forEach((source, index) => {
        const item = document.createElement("li");

        const filename =
            source.filename ||
            source.file_name ||
            source.document_name ||
            `Source ${index + 1}`;

        item.textContent = filename;
        list.appendChild(item);
    });

    section.appendChild(list);
    chatMessages.appendChild(section);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send a question to FastAPI.
chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    addMessage(question, "user");

    questionInput.value = "";
    sendButton.disabled = true;
    sendButton.textContent = "…";

    const loadingMessage = addMessage("Thinking...", "assistant");

    try {
        const response = await fetch(`${API_BASE_URL}/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                question: question,
                conversation_id: conversationId
            })
        });

        const data = await response.json();
        allDocuments = data;

        if (!response.ok) {
            throw new Error(
                data.detail || `Request failed (${response.status})`
            );
        }

        loadingMessage.textContent =
            data.answer || "The API returned no answer.";

        if (data.conversation_id !== undefined) {
            conversationId = data.conversation_id;
        }

        addSources(data.sources);
    } catch (error) {
        loadingMessage.textContent =
            `Sorry, something went wrong: ${error.message}`;

        console.error("NexusAI API error:", error);
    } finally {
        sendButton.disabled = false;
        sendButton.textContent = "↑";
        questionInput.focus();
    }
});

// Start a fresh conversation.
newChatButton.addEventListener("click", () => {
    conversationId = null;
    chatMessages.innerHTML = `
        <div class="welcome">
            <div class="welcome-icon">✦</div>
            <h1>Your knowledge, connected.</h1>
            <p>Ask a question about your documents.</p>
        </div>
    `;
    questionInput.value = "";
    questionInput.focus();
});

// Allow suggestion buttons to fill the input.
document.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
        questionInput.value = button.textContent.trim();
        questionInput.focus();
    });
});

checkApiStatus();


async function deleteConversation(id) {
    if (!accessToken) {
        alert("Please log in first.");
        return;
    }

    if (!confirm("Are you sure you want to delete this conversation?")) {
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE_URL}/conversations/${id}`,
            {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${accessToken}`
                }
            }
        );

        if (!response.ok) {
            const data = await response.json();
            throw new Error(
                data.detail || "Failed to delete conversation."
            );
        }

        if (Number(conversationId) === Number(id)) {
            conversationId = null;

            chatMessages.innerHTML = `
                <div class="welcome">
                    <div class="welcome-icon">✦</div>
                    <h1>Your knowledge, connected.</h1>
                    <p>Ask a question about your documents.</p>
                </div>
            `;
        }

        await loadChatHistory();
        alert("Conversation deleted successfully!");
    } catch (error) {
        alert(`Delete failed: ${error.message}`);
    }
}


const logoutButton = document.getElementById("logout-btn");

logoutButton.addEventListener("click", () => {
    // Clear the login token
    accessToken = null;

        // Clear previous user's chat history and messages
    conversationHistory.replaceChildren();
    document.getElementById("chat-messages").replaceChildren();

    // Clear previous user's document list
    const documentsList = document.getElementById("documents-list");
    if (documentsList) {
        documentsList.replaceChildren();
    }

    // Show the login card again
    document.getElementById("login-section").style.display = "block";

    // Hide the chat interface
    document.getElementById("chat-messages").style.display = "none";
    document.getElementById("chat-form").style.display = "none";

    // Reset the email badge
    document.getElementById("user-badge").textContent = "User";

    // Clear login fields and status
    loginForm.reset();
    loginStatus.textContent = "";

    console.log("Logged out successfully.");
});
