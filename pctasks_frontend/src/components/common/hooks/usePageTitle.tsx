export const usePageTitle = (title?: string) => {
  const defaultTitle = "PC Tasks";
  document.title = title ? `${defaultTitle} | ${title}` : defaultTitle;
  return null;
};
