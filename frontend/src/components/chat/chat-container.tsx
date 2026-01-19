"use client";

import { useEffect, useRef, useCallback } from "react";
import { useChat, useLocalChat } from "@/hooks";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { Button } from "@/components/ui";
import { Wifi, WifiOff, RotateCcw, Bot } from "lucide-react";

function LocalChatContainer() {
  const { messages, isConnected, isProcessing, connect, disconnect, sendMessage, clearMessages } =
    useLocalChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ChatUI
      messages={messages}
      isConnected={isConnected}
      isProcessing={isProcessing}
      sendMessage={sendMessage}
      clearMessages={clearMessages}
      messagesEndRef={messagesEndRef}
    />
  );
}
export function ChatContainer() {
  return <LocalChatContainer />;
}

interface ChatUIProps {
  messages: import("@/types").ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  sendMessage: (content: string) => void;
  clearMessages: () => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

function ChatUI({
  messages,
  isConnected,
  isProcessing,
  sendMessage,
  clearMessages,
  messagesEndRef,
}: ChatUIProps) {
  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col">
      <div className="scrollbar-thin flex-1 overflow-y-auto px-2 py-4 sm:px-4 sm:py-6">
        {messages.length === 0 ? (
          <div className="text-muted-foreground flex h-full flex-col items-center justify-center gap-4">
            <div className="bg-secondary flex h-14 w-14 items-center justify-center rounded-full sm:h-16 sm:w-16">
              <Bot className="h-7 w-7 sm:h-8 sm:w-8" />
            </div>
            <div className="px-4 text-center">
              <p className="text-foreground text-base font-medium sm:text-lg">AI Assistant</p>
              <p className="text-sm">Start a conversation to get help</p>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="px-2 pb-2 sm:px-4 sm:pb-4">
        <div className="bg-card rounded-xl border p-3 shadow-sm sm:p-4">
          <ChatInput
            onSend={sendMessage}
            disabled={!isConnected || isProcessing}
            isProcessing={isProcessing}
          />
          <div className="mt-3 flex items-center justify-between border-t pt-3">
            <div className="flex items-center gap-2">
              {isConnected ? (
                <Wifi className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <WifiOff className="h-3.5 w-3.5 text-red-500" />
              )}
              <span className="text-muted-foreground text-xs">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            <Button variant="ghost" size="sm" onClick={clearMessages} className="h-8 px-3 text-xs">
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              Reset
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
