export type UserType = "guest" | "regular";

export const auth = async () => {
  return {
    user: {
      id: "demo-user",
      email: "demo@basis.ai",
      name: "Demo User",
      type: "regular" as UserType,
    },
  };
};

export const signIn = async (_provider?: string, _options?: any) => ({ error: null });
export const signOut = async (_options?: any) => {};
