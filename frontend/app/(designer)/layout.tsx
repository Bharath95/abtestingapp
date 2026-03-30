// frontend/app/(designer)/layout.tsx
export default function DesignerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* Navbar will be added in Task 13 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </>
  );
}
