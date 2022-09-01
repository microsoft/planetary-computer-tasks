import { mergeStyleSets, Separator } from "@fluentui/react";
import { Outlet } from "react-router-dom";
import { Header } from "components/layout";

function App() {
  return (
    <div className={styles.wrapper}>
      <Header />
      <Separator />
      <main className={styles.main}>
        <div className={styles.page}>
          <Outlet />
        </div>
      </main>
      <footer>Footer</footer>
    </div>
  );
}

export default App;

const styles = mergeStyleSets({
  wrapper: {
    display: "flex",
    flexDirection: "column",
    minHeight: "100vh",
  },
  main: {
    display: "flex",
    flexDirection: "column",
    flexGrow: 1,
    margin: "0 20px",
  },
  page: {
    flexGrow: 1,
    display: "flex",
    flexDirection: "column",
  },
});
