export const mergeClassNames = (...classNames: string[]) => {
  return classNames.filter(Boolean).join(" ");
};
