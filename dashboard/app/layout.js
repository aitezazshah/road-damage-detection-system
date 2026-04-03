import "./globals.css";

export const metadata = {
  title: "InspectRAIL — City Dashboard",
  description: "Road inspection reports for city authorities",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
