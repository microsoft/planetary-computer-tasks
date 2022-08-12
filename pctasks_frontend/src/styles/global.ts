import { getTheme, IStackTokens, IStyle } from "@fluentui/react";

const theme = getTheme();
export const treeIndent = 30;

export const gapRegular: IStackTokens = {
  childrenGap: 8,
};

export const gapSmall: IStackTokens = {
  childrenGap: 4,
};

export const borderColor = theme.palette.neutralLight;
export const border: IStyle = {
  borderColor: borderColor,
  borderStyle: "solid",
  borderWidth: 1,
};
export const borderTop: IStyle = {
  ...border,
  borderLeftWidth: 0,
  borderRightWidth: 0,
  borderBottomWidth: 0,
};

export const borderRound: IStyle = {
  ...border,
  borderRadius: 4,
};
