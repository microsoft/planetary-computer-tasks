import { mergeStyleSets, Stack, Text } from "@fluentui/react";
import { NavLink } from "react-router-dom";
import { gapRegular } from "styles/global";

export const Header = () => {
  return (
    <nav className={styles.header}>
      <Stack horizontal wrap verticalAlign="center" tokens={gapRegular}>
        <a
          className={styles.logoLink}
          href="https://www.microsoft.com"
          aria-label="Microsoft"
        >
          <img
            className={styles.logoImageStyle}
            alt=""
            src="https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RE1Mu3b?ver=5c31"
            role="presentation"
            aria-hidden="true"
          />
        </a>
        <div className={styles.headerPipeStyle}>|</div>
        <Text className={styles.title} variant="large">
          PC Tasks
        </Text>
        <NavLink to={"workflows"}>Workflows</NavLink>
      </Stack>
    </nav>
  );
};

const styles = mergeStyleSets({
  header: {
    margin: "20px 20px 0 20px",
  },
  logoLink: {
    width: "113px",
    outlineOffset: "-2px",
    display: "flex",
    alignItems: "center",
  },

  logoImageStyle: {
    maxWidth: "none",
    width: "108px",
    lineHeight: "1",
  },

  headerPipeStyle: {
    marginTop: "0px !important",
    marginLeft: "7px !important",
    marginRight: "14px !important",
    fontSize: "23.5px",
    fontWeight: 500,
    lineHeight: "1",
  },
  title: {
    marginLeft: "-3px !important",
    fontWeight: "600",
  },
});
