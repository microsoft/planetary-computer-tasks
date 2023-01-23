export const getShortId = (id: string, length: number = 8): string => {
  return id.substring(0, length);
};
