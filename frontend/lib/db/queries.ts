// Stubs — no database in this demo

export async function getUser(email: string) { return []; }
export async function createUser(email: string, password: string) { return {}; }
export async function createGuestUser() { return [{ id: "guest-1", email: "guest@basis.ai" }]; }
export async function saveChat(chat: any) { return chat; }
export async function deleteChatById({ id }: { id: string }) { return { id }; }
export async function deleteAllChatsByUserId({ userId }: { userId: string }) { return; }
export async function getChatsByUserId({ userId }: { userId: string }) { return []; }
export async function getChatById({ id }: { id: string }) { return null; }
export async function saveMessages({ messages }: { messages: any[] }) { return messages; }
export async function updateMessage({ id, parts }: { id: string; parts: any }) { return { id, parts }; }
export async function getMessagesByChatId({ id }: { id: string }) { return []; }
export async function voteMessage({ chatId, messageId, type }: any) { return {}; }
export async function getVotesByChatId({ id }: { id: string }) { return []; }
export async function saveDocument({ id, title, kind, content, userId }: any) { return { id }; }
export async function updateDocumentContent({ id, content }: any) { return { id, content }; }
export async function getDocumentsById({ id }: { id: string }) { return []; }
export async function getDocumentById({ id }: { id: string }) { return null; }
export async function deleteDocumentsByIdAfterTimestamp({ id, timestamp }: any) { return; }
export async function saveSuggestions({ suggestions }: any) { return suggestions; }
export async function getSuggestionsByDocumentId({ documentId }: { documentId: string }) { return []; }
export async function getMessageCountByUserId({ id, differenceInHours }: any) { return 0; }
export async function updateChatTitleById({ chatId, title }: any) { return { chatId, title }; }
export async function createStreamId({ streamId, chatId }: any) { return; }
