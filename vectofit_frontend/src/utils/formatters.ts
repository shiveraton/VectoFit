export const capitalize = (str?: string | null): string => {
  if (!str) return "Guest";
  return str.charAt(0).toUpperCase() + str.slice(1);
};
